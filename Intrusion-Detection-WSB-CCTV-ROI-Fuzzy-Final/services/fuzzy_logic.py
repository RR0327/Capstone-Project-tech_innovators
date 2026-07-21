"""Fuzzy decision logic for ROI-based intrusion confirmation.

Workflow used by this module:
1. The primary intrusion model must detect an intrusion first.
2. The intrusion bounding box must enter the restricted ROI zone.
3. The ROI/person-context model class is then evaluated by fuzzy rules.
4. The fuzzy result becomes the final alert decision.

The logic is intentionally transparent for academic defence. It is not a hidden
black-box classifier; it is a rule-based fuzzy scoring layer that combines
intrusion confidence, ROI overlap, bounding-box size, previous risk score, and
ROI/person-context class.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, float(value)))


def normalize_label(value: Any) -> str:
    """Normalize model labels into a simple comparable format."""
    return str(value or "").strip().lower().replace("_", " ").replace("-", " ")


CLASS_ALIASES = {
    "abnormal": "abnormal person",
    "abnormal person": "abnormal person",
    "suspicious person": "abnormal person",
    "covered": "covered person",
    "covered person": "covered person",
    "masked person": "covered person",
    "normal": "normal person",
    "normal person": "normal person",
    "person": "normal person",
    "weapon": "weapon",
    "gun": "weapon",
    "knife": "weapon",
    "background": "background",
    "bg": "background",
    "none": "background",
    "": "unknown",
}


@dataclass(frozen=True)
class FuzzyRuleConfig:
    """Fuzzy scoring settings.

    The values are kept simple so they can be explained in presentation/viva.
    """

    normal_person_threshold: float = 80.0
    unknown_alert_threshold: float = 75.0
    covered_alert_threshold: float = 60.0
    abnormal_alert_threshold: float = 60.0
    weapon_alert_threshold: float = 50.0


class FuzzyIntrusionLogic:
    """Final ROI fuzzy logic after intrusion and ROI checks are complete."""

    def __init__(self, config: FuzzyRuleConfig | None = None) -> None:
        self.config = config or FuzzyRuleConfig()

    @staticmethod
    def canonical_class(label: Any) -> str:
        normalized = normalize_label(label)
        return CLASS_ALIASES.get(normalized, normalized or "unknown")

    @staticmethod
    def _context_class(detection: dict[str, Any]) -> str:
        return FuzzyIntrusionLogic.canonical_class(
            detection.get("roi_context_class")
            or detection.get("detected_class")
            or detection.get("context_class")
            or "unknown"
        )

    def evaluate(self, detection: dict[str, Any] | None) -> dict[str, Any]:
        """Evaluate one intrusion detection after ROI analysis.

        Returns a dictionary that can be shown directly in UI/reporting.
        """
        if not detection:
            return {
                "fuzzy_status": "not_applicable",
                "fuzzy_class": "none",
                "fuzzy_score": 0.0,
                "risk_level": "none",
                "should_alert": False,
                "reason": "No intrusion detection was available for fuzzy logic.",
            }

        inside_roi = bool(detection.get("inside_roi") or detection.get("roi_entered"))
        if not inside_roi:
            return {
                "fuzzy_status": "not_applicable",
                "fuzzy_class": "outside_roi",
                "fuzzy_score": 0.0,
                "risk_level": "low",
                "should_alert": False,
                "reason": "Intrusion was detected, but its bounding box did not enter the restricted ROI.",
            }

        class_name = self._context_class(detection)
        intrusion_confidence = float(detection.get("confidence", 0.0) or 0.0)
        class_confidence = float(detection.get("roi_context_confidence", 0.0) or 0.0)
        roi_overlap = float(detection.get("roi_overlap_ratio", 0.0) or 0.0)
        bbox_area_ratio = float(detection.get("bbox_area_ratio", 0.0) or 0.0)
        previous_risk = float(detection.get("risk_score", 0.0) or 0.0)

        # Fuzzy memberships converted into transparent partial scores.
        intrusion_strength = _clamp(intrusion_confidence * 100.0)
        context_strength = _clamp(class_confidence * 100.0)
        roi_strength = _clamp(roi_overlap * 150.0)
        size_strength = _clamp(bbox_area_ratio * 350.0)
        hybrid_strength = _clamp(previous_risk)

        # Base score: intrusion + ROI + visual size + prior hybrid risk.
        score = (
            intrusion_strength * 0.30
            + context_strength * 0.20
            + roi_strength * 0.20
            + size_strength * 0.10
            + hybrid_strength * 0.20
        )

        # Class-specific fuzzy weighting.
        if class_name == "weapon":
            score += 45
            should_alert = score >= self.config.weapon_alert_threshold
            risk_level = "critical"
            alert_type = "critical_weapon_roi_intrusion"
            reason = "Weapon detected inside restricted ROI after intrusion detection."
        elif class_name == "abnormal person":
            score += 35
            should_alert = score >= self.config.abnormal_alert_threshold
            risk_level = "high"
            alert_type = "abnormal_person_roi_intrusion"
            reason = "Abnormal person detected inside restricted ROI after intrusion detection."
        elif class_name == "covered person":
            score += 30
            should_alert = score >= self.config.covered_alert_threshold
            risk_level = "high"
            alert_type = "covered_person_roi_intrusion"
            reason = "Covered person detected inside restricted ROI after intrusion detection."
        elif class_name == "normal person":
            score -= 15
            should_alert = score >= self.config.normal_person_threshold
            risk_level = "medium" if should_alert else "low"
            alert_type = "normal_person_roi_review" if should_alert else "normal_person_roi_no_alert"
            reason = (
                "Normal person detected inside restricted ROI. Fuzzy score is high enough for review."
                if should_alert
                else "Normal person detected inside restricted ROI. Fuzzy logic did not confirm intrusion alert."
            )
        elif class_name == "background":
            score -= 30
            should_alert = False
            risk_level = "low"
            alert_type = "background_roi_no_alert"
            reason = "Background class detected inside ROI. Fuzzy logic rejected the alert."
        else:
            score += 10
            should_alert = score >= self.config.unknown_alert_threshold
            risk_level = "high" if should_alert else "medium"
            alert_type = "unknown_roi_intrusion_review" if should_alert else "unknown_roi_no_alert"
            reason = (
                f"Unknown or other class '{class_name}' entered restricted ROI after intrusion detection."
                if should_alert
                else f"Unknown or other class '{class_name}' entered ROI, but fuzzy score is not high enough."
            )

        score = round(_clamp(score), 2)
        return {
            "fuzzy_status": "evaluated",
            "fuzzy_class": class_name,
            "fuzzy_score": score,
            "risk_level": risk_level,
            "should_alert": bool(should_alert),
            "alert_type": alert_type,
            "reason": reason,
            "inputs": {
                "intrusion_confidence": round(intrusion_confidence, 6),
                "class_confidence": round(class_confidence, 6),
                "roi_overlap_ratio": round(roi_overlap, 6),
                "bbox_area_ratio": round(bbox_area_ratio, 6),
                "previous_risk_score": round(previous_risk, 2),
            },
        }
