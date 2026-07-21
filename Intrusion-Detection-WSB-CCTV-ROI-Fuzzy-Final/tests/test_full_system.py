"""Lightweight integration checks that do not start a camera or send email."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from services.alert_decision_logic import AlertDecisionLogic
from services.feature_extractor import FeatureExtractor
from services.risk_utils import RiskCalculator
from services.roi_utils import ROIAnalyzer


def test_hybrid_roi_fuzzy_pipeline_with_synthetic_detection():
    detection = {
        "bbox": [250, 120, 500, 430],
        "confidence": 0.86,
        "model_class": "intrusion",
        "class": "intrusion",
        "frames_seen": 4,
    }
    roi_model_detections = [
        {
            "bbox": [260, 130, 490, 420],
            "model_class": "covered person",
            "class": "covered person",
            "confidence": 0.91,
        }
    ]
    enriched = FeatureExtractor().extract_features([detection], (480, 640, 3))
    analyzer = ROIAnalyzer(
        manual_zones_json='[{"name":"restricted_area","bbox":[0.35,0.20,0.95,0.95]}]',
        require_roi_for_alert=True,
    )
    analyzed, summary = analyzer.analyze(enriched, (480, 640, 3), roi_model_detections)
    risk = RiskCalculator().compute_risk(analyzed[0], {"frames_seen": 4})
    decision = AlertDecisionLogic().decide_whether_to_alert({**analyzed[0], **risk})
    assert summary["inside_roi_count"] == 1
    assert decision["status"] == "intrusion"
    assert decision["should_alert"] is True
    assert decision["fuzzy_result"]["fuzzy_class"] == "covered person"


def test_required_web_files_exist():
    for path in (
        "app.py",
        "templates/index.html",
        "templates/live_camera.html",
        "templates/result.html",
        "static/js/camera.js",
    ):
        assert (ROOT / path).exists()
