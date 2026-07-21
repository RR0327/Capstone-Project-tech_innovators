from services.risk_utils import RiskCalculator


def test_selects_highest_hybrid_risk_not_first_item():
    detections = [
        {"model_class": "intrusion", "confidence": 0.50, "bbox_area_ratio": 0.01},
        {"model_class": "intrusion", "confidence": 0.90, "bbox_area_ratio": 0.05},
    ]
    best, risk = RiskCalculator().select_most_dangerous(detections)
    assert best is detections[1]
    assert risk["risk_score"] > 0
