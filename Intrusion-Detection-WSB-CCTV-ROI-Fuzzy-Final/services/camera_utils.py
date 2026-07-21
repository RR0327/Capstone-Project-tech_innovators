"""Server-side live camera processing for intrusion + ROI monitoring."""

from __future__ import annotations

from datetime import datetime
import threading
import time
from typing import Any

import cv2

from OPTIMIZATION_CONFIG import CAMERA
from services.alert_decision_logic import AlertDecisionLogic
from services.feature_extractor import FeatureExtractor
from services.risk_utils import RiskCalculator
from services.roi_utils import ROIAnalyzer
from services.tracker import CentroidTracker


class CameraStream:
    def __init__(
        self,
        detector,
        camera_index: int = CAMERA.camera_index,
        alert_service=None,
        cooldown_seconds: int = 60,
        frame_skip: int = CAMERA.frame_skip,
        use_flipped_camera: bool = CAMERA.flip_camera,
        save_alert_screenshots: bool = True,
        roi_detector=None,
        roi_analyzer: ROIAnalyzer | None = None,
        **_ignored,
    ) -> None:
        self.detector = detector
        self.roi_detector = roi_detector
        self.roi_analyzer = roi_analyzer
        self.alert_service = alert_service
        self.cooldown_seconds = int(cooldown_seconds)
        self.frame_skip = max(1, int(frame_skip))
        self.use_flipped_camera = bool(use_flipped_camera)
        self.save_alert_screenshots = bool(save_alert_screenshots)

        self.camera = cv2.VideoCapture(camera_index)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA.width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA.height)
        self.camera.set(cv2.CAP_PROP_FPS, CAMERA.fps)
        self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not self.camera.isOpened():
            raise RuntimeError(f"Could not open camera index {camera_index}.")

        self.tracker = CentroidTracker()
        self.feature_extractor = FeatureExtractor()
        self.risk_calculator = RiskCalculator()
        self.alert_logic = AlertDecisionLogic()

        self.running = False
        self.thread: threading.Thread | None = None
        self.frame_lock = threading.Lock()
        self.latest_frame = None
        self.frame_count = 0
        self.last_alert_time = 0.0
        self.detection_info: dict[str, Any] = {
            "count": 0,
            "detections": [],
            "status": "camera_stopped",
            "decision": self.alert_logic.non_intrusion("Camera is not running."),
            "roi_summary": {"enabled": bool(self.roi_detector and self.roi_analyzer)},
        }

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._process_frames, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        self.camera.release()

    def _run_roi(self, frame, detections: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
        if not self.roi_analyzer:
            return detections, {"enabled": False}, []
        roi_detections: list[dict[str, Any]] = []
        if self.roi_detector:
            _, roi_detections = self.roi_detector.predict_frame(frame)
        # Manual ROI zones work independently of the optional ROI model.
        analyzed, summary = self.roi_analyzer.analyze(detections, frame.shape, roi_detections)
        summary["roi_model_loaded"] = self.roi_detector is not None
        return analyzed, summary, roi_detections

    def _process_frames(self) -> None:
        while self.running and self.camera.isOpened():
            success, frame = self.camera.read()
            if not success:
                time.sleep(0.05)
                continue
            if self.use_flipped_camera:
                frame = cv2.flip(frame, 1)

            self.frame_count += 1
            if self.frame_count % self.frame_skip != 0:
                with self.frame_lock:
                    self.latest_frame = frame
                continue

            try:
                annotated, detections = self.detector.predict_frame(frame)
                enriched = self.feature_extractor.extract_features(detections, frame.shape)
                enriched, roi_summary, roi_detections = self._run_roi(frame, enriched)
                if self.roi_analyzer:
                    annotated = self.roi_analyzer.draw_overlay(annotated, frame.shape, roi_detections)

                tracked_objects = self.tracker.update(enriched)

                for detection in enriched:
                    track_id = detection.get("track_id")
                    if track_id in tracked_objects:
                        obj = tracked_objects[track_id]
                        detection["frames_seen"] = obj["frames_seen"]
                        detection["velocity"] = obj["velocity"]
                        detection["area_growth"] = obj["area_growth"]
                        x1, y1, _, _ = detection["bbox"]
                        cv2.putText(
                            annotated,
                            f"Track {track_id}",
                            (x1, max(20, y1 - 24)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (255, 255, 0),
                            1,
                            cv2.LINE_AA,
                        )

                best_detection, risk_info = self.risk_calculator.select_most_dangerous(
                    enriched, tracked_objects, frame.shape
                )
                if best_detection:
                    combined = {**best_detection, **(risk_info or {})}
                    decision = self.alert_logic.decide_whether_to_alert(combined)
                    fuzzy_result = decision.get("fuzzy_result") or {}
                    best_detection.update({
                        "risk_score": combined.get("risk_score"),
                        "risk_level": combined.get("risk_level"),
                        "fuzzy_result": decision.get("fuzzy_result"),
                        "fuzzy_class": fuzzy_result.get("fuzzy_class"),
                        "fuzzy_score": fuzzy_result.get("fuzzy_score"),
                        "fuzzy_risk_level": fuzzy_result.get("risk_level"),
                    })
                else:
                    decision = self.alert_logic.non_intrusion()

                for detection in enriched:
                    risk = self.risk_calculator.compute_risk(
                        detection,
                        tracked_objects.get(detection.get("track_id"))
                        if detection.get("track_id") in tracked_objects
                        else None,
                        frame.shape,
                    )
                    detection.update(risk)

                self.detection_info = {
                    "count": len(enriched),
                    "detections": enriched,
                    "roi_detections": roi_detections,
                    "roi_summary": roi_summary,
                    "status": decision["status"],
                    "decision": decision,
                }

                if decision.get("should_alert") and self.alert_service:
                    now = time.time()
                    if now - self.last_alert_time >= self.cooldown_seconds:
                        screenshot = (
                            self.alert_service.save_screenshot(annotated)
                            if self.save_alert_screenshots
                            else None
                        )
                        self.alert_service.send_intrusion_alert(
                            screenshot,
                            {
                                "source": "Live camera",
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "confidence": best_detection.get("confidence", 0),
                                "risk_score": decision.get("risk_score", 0),
                                "reason": decision.get("reason", ""),
                                "track_id": best_detection.get("track_id"),
                                "roi_status": best_detection.get("roi_status"),
                                "roi_zone": best_detection.get("roi_zone_name"),
                                "roi_context": best_detection.get("roi_context_class"),
                                "fuzzy_class": best_detection.get("fuzzy_class"),
                                "fuzzy_score": best_detection.get("fuzzy_score"),
                            },
                        )
                        self.last_alert_time = now

                with self.frame_lock:
                    self.latest_frame = annotated
            except Exception as exc:
                print(f"Camera processing error: {exc}")
                with self.frame_lock:
                    self.latest_frame = frame

    def get_frame(self):
        with self.frame_lock:
            return None if self.latest_frame is None else self.latest_frame.copy()

    @staticmethod
    def encode_frame(frame) -> bytes:
        success, buffer = cv2.imencode(
            ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), CAMERA.jpeg_quality]
        )
        if not success:
            raise RuntimeError("Could not encode camera frame.")
        return buffer.tobytes()

    def get_detections(self) -> dict[str, Any]:
        return self.detection_info
