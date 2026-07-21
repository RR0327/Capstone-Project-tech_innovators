from services.roi_utils import ROIAnalyzer, center_inside, intersection_ratio
from services.risk_utils import RiskCalculator
from services.alert_decision_logic import AlertDecisionLogic


def test_center_inside_roi_box():
    assert center_inside([40, 40, 80, 80], [0, 0, 100, 100]) is True
    assert center_inside([140, 140, 180, 180], [0, 0, 100, 100]) is False


def test_intersection_ratio_for_half_overlap():
    ratio = intersection_ratio([0, 0, 100, 100], [50, 0, 150, 100])
    assert round(ratio, 2) == 0.50


def test_manual_roi_marks_detection_inside():
    analyzer = ROIAnalyzer(
        manual_zones_json='[{"name":"counter","x1":0.0,"y1":0.0,"x2":0.5,"y2":1.0}]',
        require_roi_for_alert=True,
    )
    detections = [{"bbox": [20, 20, 100, 200], "confidence": 0.90, "model_class": "intrusion"}]
    analyzed, summary = analyzer.analyze(detections, (400, 400, 3), [])
    assert summary["manual_zone_count"] == 1
    assert analyzed[0]["inside_roi"] is True
    assert analyzed[0]["roi_entered"] is True
    assert analyzed[0]["roi_zone_name"] == "counter"
    assert analyzed[0]["roi_required"] is True


def test_roi_requirement_blocks_outside_detection():
    decision = AlertDecisionLogic(require_roi_for_alert=True).decide_whether_to_alert(
        {
            "bbox": [250, 20, 350, 200],
            "confidence": 0.95,
            "model_class": "intrusion",
            "inside_roi": False,
            "roi_required": True,
        }
    )
    assert decision["should_alert"] is False
    assert decision["status"] == "non_intrusion"


def test_roi_person_context_adds_risk_bonus():
    base = {
        "bbox": [10, 10, 100, 200],
        "confidence": 0.80,
        "bbox_area_ratio": 0.10,
        "roi_person_alert": True,
    }
    risk = RiskCalculator().compute_risk(base, {"frames_seen": 1})
    assert risk["components"]["roi_bonus"] == 15.0
