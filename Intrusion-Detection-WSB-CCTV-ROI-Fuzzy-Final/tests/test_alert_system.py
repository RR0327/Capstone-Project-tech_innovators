from services.alert_decision_logic import AlertDecisionLogic, get_email_title_and_message


def test_alert_message_for_roi_intrusion():
    decision = AlertDecisionLogic().decide_whether_to_alert(
        {
            "model_class": "intrusion",
            "confidence": 0.90,
            "risk_score": 90,
            "inside_roi": True,
            "roi_overlap_ratio": 0.50,
            "bbox_area_ratio": 0.20,
            "roi_context_class": "weapon",
            "roi_context_confidence": 0.95,
        }
    )
    email = get_email_title_and_message(decision)
    assert decision["should_alert"]
    assert "ROI INTRUSION" in email["title"]
    assert email["urgency"] == "CRITICAL"


def test_normal_message_for_no_detection():
    decision = AlertDecisionLogic().non_intrusion()
    email = get_email_title_and_message(decision)
    assert not decision["should_alert"]
    assert email["urgency"] == "NORMAL"
