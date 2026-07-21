"""Hybrid risk scoring from model, geometry, and tracking signals."""

from __future__ import annotations

from typing import Any


class RiskCalculator:
    def __init__(
        self,
        confidence_weight: float = 0.55,
        area_weight: float = 0.15,
        persistence_weight: float = 0.20,
        motion_weight: float = 0.10,
    ) -> None:
        self.confidence_weight = confidence_weight
        self.area_weight = area_weight
        self.persistence_weight = persistence_weight
        self.motion_weight = motion_weight

    @staticmethod
    def _tracking_values(tracking_info: dict[str, Any] | None) -> tuple[float, float, float]:
        if not tracking_info:
            return 1.0, 0.0, 0.0
        frames_seen = float(tracking_info.get("frames_seen", 1))
        velocity = tracking_info.get("velocity", (0.0, 0.0))
        speed = (float(velocity[0]) ** 2 + float(velocity[1]) ** 2) ** 0.5
        growth = float(tracking_info.get("area_growth", 0.0))
        return frames_seen, speed, growth

    def compute_risk(
        self,
        detection: dict[str, Any],
        tracking_info: dict[str, Any] | None = None,
        frame_shape: tuple[int, ...] | None = None,
    ) -> dict[str, Any]:
        confidence = max(0.0, min(1.0, float(detection.get("confidence", 0.0))))
        area_ratio = float(detection.get("bbox_area_ratio", 0.0))
        if area_ratio <= 0 and frame_shape is not None:
            x1, y1, x2, y2 = detection.get("bbox", [0, 0, 0, 0])
            area_ratio = max(0, (x2 - x1) * (y2 - y1)) / max(
                1, frame_shape[0] * frame_shape[1]
            )

        frames_seen, speed, growth = self._tracking_values(tracking_info)
        confidence_score = confidence * 100
        # A box covering 25% of a frame reaches the maximum area contribution.
        area_score = min(100.0, max(0.0, area_ratio) * 400.0)
        persistence_score = min(100.0, frames_seen * 12.5)
        motion_score = min(100.0, speed * 2.0 + max(0.0, growth) * 100.0)

        base_risk = (
            self.confidence_weight * confidence_score
            + self.area_weight * area_score
            + self.persistence_weight * persistence_score
            + self.motion_weight * motion_score
        )

        roi_bonus = 0.0
        if detection.get("inside_roi"):
            roi_bonus += 10.0
        if detection.get("roi_person_alert"):
            roi_bonus += 15.0

        risk = max(0.0, min(100.0, base_risk + roi_bonus))

        return {
            "risk_score": round(risk, 2),
            "risk_level": self._risk_level(risk),
            "frames_seen": int(frames_seen),
            "components": {
                "confidence": round(confidence_score, 2),
                "area": round(area_score, 2),
                "persistence": round(persistence_score, 2),
                "motion": round(motion_score, 2),
                "roi_bonus": round(roi_bonus, 2),
            },
        }

    def select_most_dangerous(
        self,
        detections: list[dict[str, Any]],
        tracked_objects: dict[int, dict[str, Any]] | None = None,
        frame_shape: tuple[int, ...] | None = None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        best_detection = None
        best_risk = None
        best_score = -1.0

        for detection in detections:
            tracking = None
            track_id = detection.get("track_id")
            if tracked_objects is not None and track_id in tracked_objects:
                tracking = tracked_objects[track_id]
            risk = self.compute_risk(detection, tracking, frame_shape)
            if risk["risk_score"] > best_score:
                best_score = risk["risk_score"]
                best_detection = detection
                best_risk = risk
        return best_detection, best_risk

    @staticmethod
    def _risk_level(score: float) -> str:
        if score >= 80:
            return "critical"
        if score >= 65:
            return "high"
        if score >= 40:
            return "medium"
        return "low"
