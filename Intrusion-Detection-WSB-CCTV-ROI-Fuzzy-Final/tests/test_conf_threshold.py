from services.alert_decision_logic import AlertDecisionLogic


def test_below_review_threshold_does_not_alert_even_inside_roi_for_normal_class():
    logic = AlertDecisionLogic(review_confidence=0.45)
    decision = logic.decide_whether_to_alert(
        {
            "model_class": "intrusion",
            "confidence": 0.44,
            "risk_score": 40,
            "frames_seen": 10,
            "inside_roi": True,
            "roi_overlap_ratio": 0.20,
            "bbox_area_ratio": 0.05,
            "roi_context_class": "normal person",
            "roi_context_confidence": 0.80,
        }
    )
    assert decision["should_alert"] is False


def test_review_threshold_with_weapon_inside_roi_alerts():
    logic = AlertDecisionLogic(review_confidence=0.45)
    decision = logic.decide_whether_to_alert(
        {
            "model_class": "intrusion",
            "confidence": 0.45,
            "risk_score": 70,
            "frames_seen": 3,
            "inside_roi": True,
            "roi_overlap_ratio": 0.45,
            "bbox_area_ratio": 0.15,
            "roi_context_class": "weapon",
            "roi_context_confidence": 0.90,
        }
    )
    assert decision["should_alert"] is True
