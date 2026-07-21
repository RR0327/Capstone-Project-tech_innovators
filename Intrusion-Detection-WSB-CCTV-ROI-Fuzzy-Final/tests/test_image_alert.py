from services.alert_decision_logic import AlertDecisionLogic


def test_image_roi_fuzzy_decision_controls_alert():
    logic = AlertDecisionLogic()
    normal = logic.decide_whether_to_alert(
        {
            "model_class": "intrusion",
            "confidence": 0.90,
            "risk_score": 50,
            "frames_seen": 1,
            "inside_roi": True,
            "roi_overlap_ratio": 0.40,
            "bbox_area_ratio": 0.15,
            "roi_context_class": "normal person",
            "roi_context_confidence": 0.90,
        }
    )
    covered = logic.decide_whether_to_alert(
        {
            "model_class": "intrusion",
            "confidence": 0.90,
            "risk_score": 50,
            "frames_seen": 1,
            "inside_roi": True,
            "roi_overlap_ratio": 0.40,
            "bbox_area_ratio": 0.15,
            "roi_context_class": "covered person",
            "roi_context_confidence": 0.90,
        }
    )
    assert normal["should_alert"] is False
    assert covered["should_alert"] is True
