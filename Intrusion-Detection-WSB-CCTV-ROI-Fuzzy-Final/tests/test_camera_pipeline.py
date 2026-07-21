import time

import numpy as np

import services.camera_utils as camera_utils
from services.camera_utils import CameraStream
from services.roi_utils import ROIAnalyzer


class FakeCapture:
    def __init__(self, _index):
        self.opened = True
        self.frames_left = 8

    def set(self, *_args):
        return True

    def isOpened(self):
        return self.opened

    def read(self):
        if self.frames_left > 0:
            self.frames_left -= 1
            return True, np.zeros((240, 320, 3), dtype=np.uint8)
        time.sleep(0.01)
        return False, None

    def release(self):
        self.opened = False


class FakeDetector:
    def predict_frame(self, frame):
        detection = {
            "bbox": [60, 30, 220, 220],
            "confidence": 0.92,
            "model_class": "intrusion",
            "class": "intrusion",
        }
        return frame.copy(), [detection]


class FakeROIDetector:
    def predict_frame(self, frame):
        return frame.copy(), [
            {
                "bbox": [70, 40, 210, 220],
                "confidence": 0.90,
                "model_class": "covered person",
                "class": "covered person",
            }
        ]


def test_live_camera_processing_with_simulated_camera(monkeypatch):
    monkeypatch.setattr(camera_utils.cv2, "VideoCapture", FakeCapture)
    stream = CameraStream(
        detector=FakeDetector(),
        camera_index=0,
        alert_service=None,
        frame_skip=1,
        roi_detector=FakeROIDetector(),
        roi_analyzer=ROIAnalyzer(
            manual_zones_json='[{"name":"restricted_area","bbox":[0.10,0.05,0.95,0.95]}]',
            require_roi_for_alert=True,
        ),
    )
    stream.start()
    deadline = time.time() + 2
    while time.time() < deadline:
        if stream.get_detections().get("status") == "intrusion":
            break
        time.sleep(0.02)
    info = stream.get_detections()
    stream.stop()
    assert info["status"] == "intrusion"
    assert info["decision"]["should_alert"] is True
    assert info["decision"]["fuzzy_result"]["fuzzy_class"] == "covered person"
    assert info["count"] == 1


def test_manual_roi_works_without_secondary_model(monkeypatch):
    monkeypatch.setattr(camera_utils.cv2, "VideoCapture", FakeCapture)
    stream = CameraStream(
        detector=FakeDetector(),
        camera_index=0,
        alert_service=None,
        frame_skip=1,
        roi_detector=None,
        roi_analyzer=ROIAnalyzer(
            manual_zones_json='[{"name":"restricted_area","bbox":[0.10,0.05,0.95,0.95]}]',
            require_roi_for_alert=True,
        ),
    )
    stream.start()
    deadline = time.time() + 2
    while time.time() < deadline:
        info = stream.get_detections()
        if info.get("roi_summary", {}).get("inside_roi_count") == 1:
            break
        time.sleep(0.02)
    info = stream.get_detections()
    stream.stop()
    assert info["roi_summary"]["inside_roi_count"] == 1
    assert info["roi_summary"]["roi_model_loaded"] is False
