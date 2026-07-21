"""Final decision rules for intrusion + ROI + fuzzy logic."""

from __future__ import annotations

from typing import Any

from OPTIMIZATION_CONFIG import DECISION
from services.fuzzy_logic import FuzzyIntrusionLogic


class AlertDecisionLogic:
    """
    Final workflow used by the updated project.

    1. Primary model checks intrusion.
    2. If no intrusion is detected, no alert is generated.
    3. If intrusion is detected, the intrusion bounding box is checked against
       the restricted ROI area.
    4. If the bounding box does not enter ROI, no ROI alert is generated.
    5. If the bounding box enters ROI, the ROI/person-context class is passed to
       fuzzy logic.
    6. Fuzzy logic confirms whether the final alert should be sent.
    """

    def __init__(
        self,
        high_confidence: float = DECISION.high_confidence,
        review_confidence: float = DECISION.review_confidence,
        risk_threshold: float = DECISION.risk_threshold,
        minimum_persistence_frames: int = DECISION.minimum_persistence_frames,
        require_roi_for_alert: bool = DECISION.require_roi_for_alert,
        fuzzy_logic: FuzzyIntrusionLogic | None = None,
    ) -> None:
        self.high_confidence = float(high_confidence)
        self.review_confidence = float(review_confidence)
        self.risk_threshold = float(risk_threshold)
        self.minimum_persistence_frames = int(minimum_persistence_frames)
        self.require_roi_for_alert = bool(require_roi_for_alert)
        self.fuzzy_logic = fuzzy_logic or FuzzyIntrusionLogic()

    @staticmethod
    def non_intrusion(reason: str = "No intrusion was detected.") -> dict[str, Any]:
        return {
            "status": "non_intrusion",
            "should_alert": False,
            "alert_type": "no_alert",
            "risk_score": 0.0,
            "reason": reason,
            "fuzzy_result": None,
        }

    @staticmethod
    def _is_intrusion_class(model_class: str) -> bool:
        value = str(model_class or "").lower()
        return "intrusion" in value and "non" not in value

    @staticmethod
    def _roi_reason(detection: dict[str, Any]) -> str:
        zone = detection.get("roi_zone_name") or "restricted ROI"
        overlap = float(detection.get("roi_overlap_ratio", 0.0) or 0.0)
        return f"Intrusion bounding box entered {zone} with {overlap:.1%} overlap."

    def _legacy_intrusion_decision(self, detection: dict[str, Any]) -> dict[str, Any]:
        """Fallback only when ROI requirement is explicitly disabled.

        The new project should normally keep REQUIRE_ROI_FOR_ALERT=true.
        This fallback is kept so developers can still run simple model tests.
        """
        confidence = float(detection.get("confidence", 0.0) or 0.0)
        risk_score = float(detection.get("risk_score", 0.0) or 0.0)
        frames_seen = int(detection.get("frames_seen", 1) or 1)

        if confidence >= self.high_confidence:
            return {
                "status": "intrusion",
                "should_alert": True,
                "alert_type": "intrusion_detected_outside_roi_mode",
                "risk_score": round(max(risk_score, confidence * 100), 2),
                "reason": f"High-confidence intrusion detected ({confidence:.1%}). ROI requirement is disabled.",
                "fuzzy_result": None,
            }

        if (
            confidence >= self.review_confidence
            and risk_score >= self.risk_threshold
            and frames_seen >= self.minimum_persistence_frames
        ):
            return {
                "status": "intrusion",
                "should_alert": True,
                "alert_type": "hybrid_intrusion_detected_outside_roi_mode",
                "risk_score": round(risk_score, 2),
                "reason": "Intrusion supported by model confidence, risk score, and persistence. ROI requirement is disabled.",
                "fuzzy_result": None,
            }

        return {
            "status": "non_intrusion",
            "should_alert": False,
            "alert_type": "no_alert",
            "risk_score": round(risk_score, 2),
            "reason": (
                f"Candidate intrusion did not meet non-ROI alert rules: confidence "
                f"{confidence:.1%}, risk {risk_score:.1f}, frames {frames_seen}."
            ),
            "fuzzy_result": None,
        }

    def decide_whether_to_alert(self, detection: dict[str, Any] | None) -> dict[str, Any]:
        if not detection:
            return self.non_intrusion()

        model_class = str(detection.get("model_class", detection.get("class", "")))
        confidence = float(detection.get("confidence", 0.0) or 0.0)
        risk_score = float(detection.get("risk_score", 0.0) or 0.0)

        # Step 1: primary model must detect intrusion first.
        if not self._is_intrusion_class(model_class):
            return self.non_intrusion("The primary model did not return the intrusion class.")

        # Step 2: ROI gate. In the final workflow, fuzzy logic runs only after
        # the intrusion bounding box enters the restricted ROI.
        inside_roi = bool(detection.get("inside_roi") or detection.get("roi_entered"))
        roi_required = bool(detection.get("roi_required", self.require_roi_for_alert))
        if roi_required and not inside_roi:
            return {
                "status": "non_intrusion",
                "should_alert": False,
                "alert_type": "intrusion_outside_roi_no_alert",
                "risk_score": round(risk_score, 2),
                "reason": "Intrusion was detected, but the bounding box did not enter the restricted ROI. No alert generated.",
                "fuzzy_result": self.fuzzy_logic.evaluate(detection),
            }

        if not inside_roi and not roi_required:
            return self._legacy_intrusion_decision(detection)

        # Step 3: fuzzy class/person-type decision.
        fuzzy_result = self.fuzzy_logic.evaluate(detection)
        detection["fuzzy_result"] = fuzzy_result
        detection["fuzzy_class"] = fuzzy_result.get("fuzzy_class")
        detection["fuzzy_score"] = fuzzy_result.get("fuzzy_score")
        detection["fuzzy_risk_level"] = fuzzy_result.get("risk_level")

        if fuzzy_result.get("should_alert"):
            return {
                "status": "intrusion",
                "should_alert": True,
                "alert_type": fuzzy_result.get("alert_type", "roi_fuzzy_intrusion"),
                "risk_score": round(max(risk_score, float(fuzzy_result.get("fuzzy_score", 0.0))), 2),
                "reason": f"{self._roi_reason(detection)} {fuzzy_result.get('reason')}",
                "fuzzy_result": fuzzy_result,
            }

        return {
            "status": "non_intrusion",
            "should_alert": False,
            "alert_type": fuzzy_result.get("alert_type", "roi_fuzzy_no_alert"),
            "risk_score": round(max(risk_score, float(fuzzy_result.get("fuzzy_score", 0.0))), 2),
            "reason": f"{self._roi_reason(detection)} {fuzzy_result.get('reason')}",
            "fuzzy_result": fuzzy_result,
        }


def get_email_title_and_message(decision: dict[str, Any]) -> dict[str, str]:
    fuzzy_result = decision.get("fuzzy_result") or {}
    fuzzy_class = fuzzy_result.get("fuzzy_class")
    if decision.get("should_alert"):
        urgency = "CRITICAL" if decision.get("risk_score", 0) >= 85 or fuzzy_class == "weapon" else "HIGH"
        return {
            "title": "ROI INTRUSION ALERT: Restricted-area violation detected",
            "message": str(decision.get("reason", "ROI intrusion detected.")),
            "urgency": urgency,
        }
    return {
        "title": "No ROI intrusion alert",
        "message": str(decision.get("reason", "The monitored scene is clear.")),
        "urgency": "NORMAL",
    }
