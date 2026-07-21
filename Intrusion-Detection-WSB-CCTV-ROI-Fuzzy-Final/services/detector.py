"""Ultralytics YOLO OBB detector for one-class intrusion detection."""

from __future__ import annotations

import os
import uuid
from typing import Any

import cv2
import numpy as np
try:
    from ultralytics import YOLO
except Exception:  # pragma: no cover - handled when detector is constructed
    YOLO = None


class IntrusionDetector:
    """
    Detects the trained class ``intrusion``.

    The supplied model is a one-class YOLOv8 OBB model. A non-intrusion result
    therefore means that no valid intrusion detection remains after filtering;
    it is not a second model class.
    """

    def __init__(
        self,
        model_path: str | None = None,
        conf: float = 0.25,
        iou: float = 0.40,
        opacity: float = 0.95,
        adaptive_preprocessing: bool = False,
        max_det: int = 100,
    ) -> None:
        self.model_path = model_path or os.getenv("MODEL_PATH", "Models/best.pt")
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found: {self.model_path}")

        if YOLO is None:
            raise ImportError(
                "ultralytics is required to load YOLO models. Install it with: pip install ultralytics"
            )
        self.model = YOLO(self.model_path)
        self.conf = float(conf)
        self.iou = float(iou)
        self.opacity = float(opacity)
        self.max_det = int(max_det)
        self.adaptive_preprocessing = bool(adaptive_preprocessing)
        self.device = 0 if self._cuda_available() else "cpu"
        self.names = self.model.names

        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    @staticmethod
    def _cuda_available() -> bool:
        try:
            import torch

            return bool(torch.cuda.is_available())
        except Exception:
            return False

    def model_info(self) -> dict[str, Any]:
        names = self.names
        if isinstance(names, dict):
            class_names = [str(names[k]) for k in sorted(names)]
        else:
            class_names = [str(name) for name in names]
        return {
            "model_path": self.model_path,
            "task": getattr(self.model, "task", "obb"),
            "classes": class_names,
            "class_count": len(class_names),
            "device": str(self.device),
            "confidence_threshold": self.conf,
            "iou_threshold": self.iou,
        }

    @staticmethod
    def _estimate_brightness(frame: np.ndarray) -> float:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return float(np.mean(gray))

    def _preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        if not self.adaptive_preprocessing:
            return frame

        brightness = self._estimate_brightness(frame)
        if brightness < 70:
            alpha, beta = 1.20, 18
        elif brightness > 190:
            alpha, beta = 1.05, -10
        else:
            alpha, beta = 1.0, 0

        adjusted = cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)
        lab = cv2.cvtColor(adjusted, cv2.COLOR_BGR2LAB)
        lightness, a_channel, b_channel = cv2.split(lab)
        lightness = self.clahe.apply(lightness)
        return cv2.cvtColor(
            cv2.merge((lightness, a_channel, b_channel)), cv2.COLOR_LAB2BGR
        )

    def _predict(self, frame: np.ndarray):
        prepared = self._preprocess_frame(frame)
        return self.model.predict(
            source=prepared,
            conf=self.conf,
            iou=self.iou,
            max_det=self.max_det,
            verbose=False,
            device=self.device,
        )[0]

    def predict_image(
        self, img_path: str, save_dir: str = "static/results"
    ) -> tuple[str, list[dict[str, Any]]]:
        os.makedirs(save_dir, exist_ok=True)
        image = cv2.imread(img_path)
        if image is None:
            raise FileNotFoundError(f"Image could not be opened: {img_path}")

        result = self._predict(image)
        detections = self._extract_detections(result, image.shape)
        annotated = self.draw_detections(image, detections)

        output_path = os.path.join(save_dir, f"{uuid.uuid4().hex}.jpg")
        if not cv2.imwrite(output_path, annotated):
            raise RuntimeError(f"Could not save result image: {output_path}")
        return output_path.replace("\\", "/"), detections

    def predict_frame(
        self, frame_bgr: np.ndarray
    ) -> tuple[np.ndarray, list[dict[str, Any]]]:
        if frame_bgr is None or frame_bgr.size == 0:
            return frame_bgr, []
        result = self._predict(frame_bgr)
        detections = self._extract_detections(result, frame_bgr.shape)
        return self.draw_detections(frame_bgr, detections), detections

    def _class_name(self, class_id: int, result: Any) -> str:
        names = getattr(result, "names", None) or self.names
        if isinstance(names, dict):
            return str(names.get(class_id, class_id)).lower()
        if 0 <= class_id < len(names):
            return str(names[class_id]).lower()
        return str(class_id)

    def _extract_detections(
        self, result: Any, frame_shape: tuple[int, ...]
    ) -> list[dict[str, Any]]:
        """Return one common format for regular boxes and oriented boxes."""
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

            width, height = x2 - x1, y2 - y1
            area = max(0, width * height)
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
    def draw_detections(
        frame: np.ndarray, detections: list[dict[str, Any]]
    ) -> np.ndarray:
        annotated = frame.copy()
        for detection in detections:
            x1, y1, x2, y2 = detection["bbox"]
            confidence = float(detection.get("confidence", 0.0))
            class_name = str(detection.get("model_class", "intrusion"))
            color = (0, 0, 230)

            polygon = detection.get("polygon")
            if polygon:
                points = np.asarray(polygon, dtype=np.int32).reshape((-1, 1, 2))
                cv2.polylines(annotated, [points], True, color, 2)
            else:
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            label = f"{class_name}: {confidence:.1%}"
            text_size, baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1
            )
            label_top = max(0, y1 - text_size[1] - baseline - 8)
            cv2.rectangle(
                annotated,
                (x1, label_top),
                (x1 + text_size[0] + 8, y1),
                color,
                -1,
            )
            cv2.putText(
                annotated,
                label,
                (x1 + 4, max(text_size[1] + 2, y1 - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
        return annotated


# Kept only so old imports do not crash while the project is migrated.
FireDetector = IntrusionDetector
