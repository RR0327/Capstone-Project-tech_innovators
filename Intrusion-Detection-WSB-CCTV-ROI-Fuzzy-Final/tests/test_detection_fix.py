import numpy as np

from services.detector import IntrusionDetector


class Value:
    def __init__(self, value):
        self.value = np.asarray(value)

    def __getitem__(self, index):
        return self.value[index]


class MockItem:
    def __init__(self, confidence=0.9):
        self.cls = Value([0])
        self.conf = Value([confidence])
        self.xyxy = Value([[10, 20, 110, 220]])
        self.xyxyxyxy = Value([[[10, 20], [100, 10], [110, 210], [20, 220]]])


class MockResult:
    names = {0: "intrusion"}

    def __init__(self, use_obb=True, empty_boxes_with_obb=False):
        if use_obb:
            self.boxes = [] if empty_boxes_with_obb else None
            self.obb = [MockItem()]
        else:
            self.boxes = [MockItem()]
            self.obb = None


def detector_without_model():
    detector = IntrusionDetector.__new__(IntrusionDetector)
    detector.names = {0: "intrusion"}
    return detector


def test_obb_extraction_is_not_empty():
    detections = detector_without_model()._extract_detections(
        MockResult(use_obb=True), (480, 640, 3)
    )
    assert len(detections) == 1
    assert detections[0]["detection_type"] == "obb"
    assert detections[0]["polygon"] is not None


def test_regular_box_extraction_still_works():
    detections = detector_without_model()._extract_detections(
        MockResult(use_obb=False), (480, 640, 3)
    )
    assert len(detections) == 1
    assert detections[0]["detection_type"] == "boxes"


def test_empty_boxes_do_not_hide_obb_results():
    detections = detector_without_model()._extract_detections(
        MockResult(use_obb=True, empty_boxes_with_obb=True), (480, 640, 3)
    )
    assert len(detections) == 1
    assert detections[0]["detection_type"] == "obb"
