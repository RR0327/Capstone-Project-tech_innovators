"""Handcrafted spatial features used beside the YOLO model."""

from __future__ import annotations

from typing import Any


class FeatureExtractor:
    def extract_features(
        self,
        detections: list[dict[str, Any]],
        frame_shape: tuple[int, ...] | None = None,
    ) -> list[dict[str, Any]]:
        features: list[dict[str, Any]] = []

        for detection in detections:
            item = dict(detection)
            x1, y1, x2, y2 = item.get("bbox", [0, 0, 0, 0])
            width = max(0, x2 - x1)
            height = max(0, y2 - y1)
            area_pixels = width * height

            if frame_shape is not None:
                frame_h, frame_w = frame_shape[:2]
                frame_area = max(1, frame_h * frame_w)
                area_ratio = area_pixels / frame_area
                center_x = ((x1 + x2) / 2) / max(1, frame_w)
                center_y = ((y1 + y2) / 2) / max(1, frame_h)
                edge_distance = min(center_x, 1 - center_x, center_y, 1 - center_y)
                border_proximity = max(0.0, 1.0 - min(1.0, edge_distance / 0.5))
            else:
                area_ratio = float(item.get("bbox_area_ratio", 0.0))
                center_x = float(item.get("center_x", 0.5))
                center_y = float(item.get("center_y", 0.5))
                border_proximity = 0.0

            confidence = float(item.get("confidence", 0.0))
            model_class = str(
                item.get("model_class", item.get("class", ""))
            ).lower()
            is_intrusion = "intrusion" in model_class and "non" not in model_class

            item.update(
                {
                    "bbox_area": area_pixels,
                    "bbox_area_ratio": round(area_ratio, 6),
                    "area_percent": round(area_ratio * 100, 3),
                    "center_x": round(center_x, 6),
                    "center_y": round(center_y, 6),
                    "border_proximity": round(border_proximity, 6),
                    "confidence_percent": round(confidence * 100, 2),
                    "intrusion_type": "intrusion" if is_intrusion else "unknown",
                    "is_intrusion_candidate": is_intrusion,
                }
            )
            features.append(item)
        return features
