"""Secondary YOLO detector for ROI/person-context monitoring.

The ROI model is optional. The uploaded model is stored as Models/roi_best.pt
and appears to contain the labels "Covered Person" and "Normal Person". This
service keeps it separate from the primary intrusion model so the main detector
is not overwritten.
"""

from __future__ import annotations

import os
from typing import Any

import cv2
import numpy as np

try:
    from ultralytics import YOLO
except Exception:  # pragma: no cover - handled when detector is constructed
    YOLO = None


class ROIDetector:
    """Runs the optional ROI/person-context model."""

    def __init__(
        self,
        model_path: str = "Models/roi_best.pt",
        conf: float = 0.25,
        iou: float = 0.40,
        max_det: int = 100,
    ) -> None:
        self.model_path = model_path
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"ROI model not found: {self.model_path}")
        if YOLO is None:
            raise ImportError(
                "ultralytics is required to load ROI YOLO models. Install it with: pip install ultralytics"
            )
        self.model = YOLO(self.model_path)
        self.conf = float(conf)
        self.iou = float(iou)
        self.max_det = int(max_det)
        self.device = 0 if self._cuda_available() else "cpu"
        self.names = self.model.names

    @staticmethod
    def _cuda_available() -> bool:
        try:
            import torch

            return bool(torch.cuda.is_available())
        except Exception:
            return False

    def model_info(self) -> dict[str, Any]:
        if isinstance(self.names, dict):
            class_names = [str(self.names[k]) for k in sorted(self.names)]
        else:
            class_names = [str(name) for name in self.names]
        return {
            "model_path": self.model_path,
            "task": getattr(self.model, "task", "unknown"),
            "classes": class_names,
            "class_count": len(class_names),
            "device": str(self.device),
            "confidence_threshold": self.conf,
            "iou_threshold": self.iou,
        }

    def predict_frame(self, frame_bgr: np.ndarray) -> tuple[np.ndarray, list[dict[str, Any]]]:
        if frame_bgr is None or frame_bgr.size == 0:
            return frame_bgr, []
        result = self.model.predict(
            source=frame_bgr,
            conf=self.conf,
            iou=self.iou,
            max_det=self.max_det,
            verbose=False,
            device=self.device,
        )[0]
        detections = self._extract_detections(result, frame_bgr.shape)
        return self.draw_detections(frame_bgr, detections), detections

    def _class_name(self, class_id: int, result: Any) -> str:
        names = getattr(result, "names", None) or self.names
        if isinstance(names, dict):
            return str(names.get(class_id, class_id)).lower()
        if 0 <= class_id < len(names):
            return str(names[class_id]).lower()
        return str(class_id)

    def _extract_detections(self, result: Any, frame_shape: tuple[int, ...]) -> list[dict[str, Any]]:
        frame_h, frame_w = frame_shape[:2]
        frame_area = max(1, frame_h * frame_w)
        detections: list[dict[str, Any]] = []

        boxes = getattr(result, "boxes", None)
        obb = getattr(result, "obb", None)

        def has_items(collection: Any) -> bool:
            if collection is None:
                return False
            try:
                return len(collection) > 0
            except TypeError:
                return True

        if has_items(obb):
            collection = obb
            detection_type = "obb"
        elif has_items(boxes):
            collection = boxes
            detection_type = "boxes"
        else:
            return detections

        for item in collection:
            class_id = int(float(item.cls[0]))
            confidence = float(item.conf[0])
            class_name = self._class_name(class_id, result)
            xyxy = np.asarray(item.xyxy[0].cpu() if hasattr(item.xyxy[0], "cpu") else item.xyxy[0])
            x1, y1, x2, y2 = [int(round(float(v))) for v in xyxy]
            x1 = max(0, min(frame_w - 1, x1))
            y1 = max(0, min(frame_h - 1, y1))
            x2 = max(x1 + 1, min(frame_w, x2))
            y2 = max(y1 + 1, min(frame_h, y2))

            polygon = None
            if detection_type == "obb" and hasattr(item, "xyxyxyxy"):
                raw_polygon = item.xyxyxyxy[0]
                if hasattr(raw_polygon, "cpu"):
                    raw_polygon = raw_polygon.cpu()
                polygon_array = np.asarray(raw_polygon, dtype=float).reshape(-1, 2)
                polygon = [
                    [
                        int(max(0, min(frame_w - 1, round(px)))),
                        int(max(0, min(frame_h - 1, round(py)))),
                    ]
                    for px, py in polygon_array
                ]

            area = max(0, (x2 - x1) * (y2 - y1))
            detections.append(
                {
                    "bbox": [x1, y1, x2, y2],
                    "polygon": polygon,
                    "confidence": round(confidence, 6),
                    "class_id": class_id,
                    "class": class_name,
                    "model_class": class_name,
                    "detection_type": detection_type,
                    "bbox_area": area,
                    "bbox_area_ratio": round(area / frame_area, 6),
                    "center_x": round(((x1 + x2) / 2) / frame_w, 6),
                    "center_y": round(((y1 + y2) / 2) / frame_h, 6),
                }
            )
        return detections

    @staticmethod
    def draw_detections(frame: np.ndarray, detections: list[dict[str, Any]]) -> np.ndarray:
        annotated = frame.copy()
        for detection in detections:
            x1, y1, x2, y2 = detection["bbox"]
            confidence = float(detection.get("confidence", 0.0))
            class_name = str(detection.get("model_class", "roi"))
            color = (230, 120, 0)
            polygon = detection.get("polygon")
            if polygon:
                points = np.asarray(polygon, dtype=np.int32).reshape((-1, 1, 2))
                cv2.polylines(annotated, [points], True, color, 2)
            else:
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            label = f"ROI {class_name}: {confidence:.1%}"
            cv2.putText(
                annotated,
                label,
                (x1, max(18, y1 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.50,
                color,
                2,
                cv2.LINE_AA,
            )
        return annotated
