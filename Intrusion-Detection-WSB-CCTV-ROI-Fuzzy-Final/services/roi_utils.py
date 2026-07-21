"""ROI geometry, matching, and overlay helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


def _normalize_label(value: str) -> str:
    return value.strip().lower().replace("_", " ")


def _label_set(value: str) -> set[str]:
    return {_normalize_label(part) for part in value.split(",") if part.strip()}


def _clip_box(box: list[int | float], frame_shape: tuple[int, ...]) -> list[int]:
    h, w = frame_shape[:2]
    x1, y1, x2, y2 = [float(v) for v in box]
    x1 = max(0, min(w - 1, int(round(x1))))
    y1 = max(0, min(h - 1, int(round(y1))))
    x2 = max(x1 + 1, min(w, int(round(x2))))
    y2 = max(y1 + 1, min(h, int(round(y2))))
    return [x1, y1, x2, y2]


def _maybe_denormalize(box: list[int | float], frame_shape: tuple[int, ...]) -> list[int]:
    h, w = frame_shape[:2]
    values = [float(v) for v in box]
    if all(0.0 <= v <= 1.0 for v in values):
        x1, y1, x2, y2 = values
        return _clip_box([x1 * w, y1 * h, x2 * w, y2 * h], frame_shape)
    return _clip_box(values, frame_shape)


def box_area(box: list[int | float]) -> float:
    x1, y1, x2, y2 = [float(v) for v in box]
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def intersection_ratio(inner_box: list[int | float], roi_box: list[int | float]) -> float:
    ix1 = max(float(inner_box[0]), float(roi_box[0]))
    iy1 = max(float(inner_box[1]), float(roi_box[1]))
    ix2 = min(float(inner_box[2]), float(roi_box[2]))
    iy2 = min(float(inner_box[3]), float(roi_box[3]))
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    return inter / max(1.0, box_area(inner_box))


def center_inside(box: list[int | float], roi_box: list[int | float]) -> bool:
    cx = (float(box[0]) + float(box[2])) / 2.0
    cy = (float(box[1]) + float(box[3])) / 2.0
    return float(roi_box[0]) <= cx <= float(roi_box[2]) and float(roi_box[1]) <= cy <= float(roi_box[3])


@dataclass
class ROIAnalyzer:
    manual_zones_json: str = ""
    min_overlap_ratio: float = 0.10
    use_center_check: bool = True
    zone_class_names: str = "restricted_zone,restricted area,roi,zone"
    alert_context_classes: str = "covered person,covered_person"
    require_roi_for_alert: bool = False

    @classmethod
    def from_config(cls, config) -> "ROIAnalyzer":
        return cls(
            manual_zones_json=getattr(config, "manual_zones_json", ""),
            min_overlap_ratio=float(getattr(config, "min_overlap_ratio", 0.10)),
            use_center_check=bool(getattr(config, "use_center_check", True)),
            zone_class_names=str(getattr(config, "zone_class_names", "")),
            alert_context_classes=str(getattr(config, "alert_context_classes", "")),
            require_roi_for_alert=bool(getattr(config, "require_roi_for_alert", False)),
        )

    @property
    def zone_labels(self) -> set[str]:
        return _label_set(self.zone_class_names)

    @property
    def alert_context_labels(self) -> set[str]:
        return _label_set(self.alert_context_classes)

    def parse_manual_zones(self, frame_shape: tuple[int, ...]) -> list[dict[str, Any]]:
        if not self.manual_zones_json:
            return []
        try:
            raw = json.loads(self.manual_zones_json)
        except json.JSONDecodeError:
            return []
        if isinstance(raw, dict):
            raw = [raw]
        zones: list[dict[str, Any]] = []
        for index, zone in enumerate(raw or []):
            if not isinstance(zone, dict):
                continue
            if "bbox" in zone:
                bbox = zone["bbox"]
            else:
                bbox = [zone.get("x1"), zone.get("y1"), zone.get("x2"), zone.get("y2")]
            if any(value is None for value in bbox):
                continue
            zones.append(
                {
                    "name": str(zone.get("name") or f"manual_roi_{index + 1}"),
                    "bbox": _maybe_denormalize(bbox, frame_shape),
                    "source": "manual",
                    "class": "restricted_zone",
                }
            )
        return zones

    def model_zones(self, roi_detections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        zones = []
        for index, detection in enumerate(roi_detections or []):
            label = _normalize_label(str(detection.get("model_class", detection.get("class", ""))))
            if label in self.zone_labels:
                zones.append(
                    {
                        "name": label or f"model_roi_{index + 1}",
                        "bbox": detection.get("bbox", [0, 0, 0, 0]),
                        "source": "model",
                        "class": label,
                        "confidence": detection.get("confidence", 0.0),
                    }
                )
        return zones

    def context_matches(
        self,
        detection: dict[str, Any],
        roi_detections: list[dict[str, Any]],
    ) -> tuple[dict[str, Any] | None, float]:
        best = None
        best_ratio = 0.0
        for context in roi_detections or []:
            label = _normalize_label(str(context.get("model_class", context.get("class", ""))))
            if label in self.zone_labels:
                continue
            ratio = intersection_ratio(detection.get("bbox", [0, 0, 0, 0]), context.get("bbox", [0, 0, 0, 0]))
            if ratio > best_ratio:
                best = context
                best_ratio = ratio
        return best, best_ratio

    def analyze(
        self,
        detections: list[dict[str, Any]],
        frame_shape: tuple[int, ...],
        roi_detections: list[dict[str, Any]] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        roi_detections = roi_detections or []
        zones = self.parse_manual_zones(frame_shape) + self.model_zones(roi_detections)
        output: list[dict[str, Any]] = []
        inside_count = 0
        alert_context_count = 0

        for detection in detections:
            item = dict(detection)
            best_zone = None
            best_overlap = 0.0
            inside = False
            for zone in zones:
                overlap = intersection_ratio(item.get("bbox", [0, 0, 0, 0]), zone["bbox"])
                center_ok = center_inside(item.get("bbox", [0, 0, 0, 0]), zone["bbox"])
                matched = overlap >= self.min_overlap_ratio or (self.use_center_check and center_ok)
                if matched and overlap >= best_overlap:
                    best_zone = zone
                    best_overlap = overlap
                    inside = True

            context, context_overlap = self.context_matches(item, roi_detections)
            context_label = _normalize_label(str(context.get("model_class", context.get("class", "")))) if context else ""
            context_alert = bool(context and context_label in self.alert_context_labels)

            if inside:
                inside_count += 1
            if context_alert:
                alert_context_count += 1

            item.update(
                {
                    "inside_roi": inside,
                    "roi_entered": inside,
                    "roi_required": self.require_roi_for_alert,
                    "roi_status": "inside_roi" if inside else "outside_roi",
                    "roi_zone_name": best_zone.get("name") if best_zone else None,
                    "roi_zone_source": best_zone.get("source") if best_zone else None,
                    "roi_overlap_ratio": round(best_overlap, 6),
                    "roi_context_class": context_label or None,
                    "roi_context_confidence": context.get("confidence") if context else None,
                    "roi_context_overlap": round(context_overlap, 6),
                    "roi_person_alert": context_alert,
                }
            )
            output.append(item)

        summary = {
            "enabled": True,
            "manual_zone_count": len(self.parse_manual_zones(frame_shape)),
            "model_zone_count": len(self.model_zones(roi_detections)),
            "roi_model_detection_count": len(roi_detections),
            "inside_roi_count": inside_count,
            "alert_context_count": alert_context_count,
            "fuzzy_ready_count": inside_count,
            "require_roi_for_alert": self.require_roi_for_alert,
        }
        return output, summary

    def draw_overlay(
        self,
        frame: np.ndarray,
        frame_shape: tuple[int, ...],
        roi_detections: list[dict[str, Any]] | None = None,
    ) -> np.ndarray:
        annotated = frame.copy()
        roi_detections = roi_detections or []
        zones = self.parse_manual_zones(frame_shape) + self.model_zones(roi_detections)
        for zone in zones:
            x1, y1, x2, y2 = zone["bbox"]
            color = (0, 255, 0)   # green
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                annotated,
                f"ROI: {zone['name']}",
                (x1, max(18, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
                cv2.LINE_AA,
            )
        for detection in roi_detections:
            label = _normalize_label(str(detection.get("model_class", detection.get("class", ""))))
            if label in self.zone_labels:
                continue
            x1, y1, x2, y2 = detection.get("bbox", [0, 0, 0, 0])
            color = (255, 0, 255)   # purple
            if detection.get("polygon"):
                points = np.asarray(detection["polygon"], dtype=np.int32).reshape((-1, 1, 2))
                cv2.polylines(annotated, [points], True, color, 2)
            else:
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                annotated,
                f"ROI model: {label}",
                (x1, min(frame_shape[0] - 8, y2 + 18)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.50,
                color,
                2,
                cv2.LINE_AA,
            )
        return annotated
