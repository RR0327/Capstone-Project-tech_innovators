from services.fuzzy_logic import FuzzyIntrusionLogic


def base_detection(label="covered person", confidence=0.92):
    return {
        "model_class": "intrusion",
        "confidence": 0.90,
        "inside_roi": True,
        "roi_overlap_ratio": 0.45,
        "bbox_area_ratio": 0.18,
        "risk_score": 70,
        "roi_context_class": label,
        "roi_context_confidence": confidence,
    }


def test_weapon_inside_roi_is_critical_alert():
    result = FuzzyIntrusionLogic().evaluate(base_detection("weapon", 0.95))
    assert result["should_alert"] is True
    assert result["fuzzy_class"] == "weapon"
    assert result["risk_level"] == "critical"


def test_covered_person_inside_roi_alerts():
    result = FuzzyIntrusionLogic().evaluate(base_detection("covered person", 0.91))
    assert result["should_alert"] is True
    assert result["fuzzy_class"] == "covered person"


def test_normal_person_inside_roi_is_not_automatic_alert():
    result = FuzzyIntrusionLogic().evaluate(base_detection("normal person", 0.80))
    assert result["fuzzy_class"] == "normal person"
    assert result["should_alert"] is False


def test_outside_roi_does_not_run_alert_fuzzy():
    detection = base_detection("weapon", 0.99)
    detection["inside_roi"] = False
    result = FuzzyIntrusionLogic().evaluate(detection)
    assert result["should_alert"] is False
    assert result["fuzzy_class"] == "outside_roi"
