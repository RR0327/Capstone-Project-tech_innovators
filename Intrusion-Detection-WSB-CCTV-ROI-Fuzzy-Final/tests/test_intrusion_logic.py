from services.alert_decision_logic import AlertDecisionLogic


def roi_detection(label="covered person", confidence=0.92):
    return {
        "model_class": "intrusion",
        "confidence": confidence,
        "risk_score": 70,
        "frames_seen": 4,
        "inside_roi": True,
        "roi_entered": True,
        "roi_overlap_ratio": 0.45,
        "bbox_area_ratio": 0.18,
        "roi_context_class": label,
        "roi_context_confidence": 0.91,
    }


def test_intrusion_inside_roi_with_covered_person_alerts():
    decision = AlertDecisionLogic().decide_whether_to_alert(roi_detection("covered person"))
    assert decision["should_alert"] is True
    assert decision["status"] == "intrusion"
    assert decision["fuzzy_result"]["fuzzy_class"] == "covered person"


def test_no_detection_is_non_intrusion():
    decision = AlertDecisionLogic().decide_whether_to_alert(None)
    assert decision["should_alert"] is False
    assert decision["status"] == "non_intrusion"


def test_intrusion_outside_roi_does_not_alert_when_roi_required():
    detection = roi_detection("weapon")
    detection["inside_roi"] = False
    detection["roi_entered"] = False
    decision = AlertDecisionLogic(require_roi_for_alert=True).decide_whether_to_alert(detection)
    assert decision["should_alert"] is False
    assert decision["alert_type"] == "intrusion_outside_roi_no_alert"


def test_weapon_inside_roi_creates_critical_alert():
    decision = AlertDecisionLogic().decide_whether_to_alert(roi_detection("weapon"))
    assert decision["should_alert"] is True
    assert "weapon" in decision["alert_type"]


def test_normal_person_inside_roi_is_not_automatic_alert():
    decision = AlertDecisionLogic().decide_whether_to_alert(roi_detection("normal person"))
    assert decision["should_alert"] is False
    assert decision["fuzzy_result"]["fuzzy_class"] == "normal person"
