from OPTIMIZATION_CONFIG import ALERT, CAMERA, DECISION, DETECTION


def test_default_thresholds_and_skips_are_valid():
    assert 0 <= DETECTION.image_conf <= 1
    assert 0 <= DETECTION.video_conf <= 1
    assert 0 <= DETECTION.live_conf <= 1
    assert 0 <= DETECTION.iou <= 1
    assert DETECTION.video_frame_skip >= 1
    assert 0 <= DECISION.review_confidence <= DECISION.high_confidence <= 1
    assert 0 <= DECISION.risk_threshold <= 100
    assert DECISION.minimum_persistence_frames >= 1
    assert CAMERA.frame_skip >= 1
    assert ALERT.cooldown_seconds >= 0
