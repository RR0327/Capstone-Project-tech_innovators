"""Uploaded-video processing with tracking, ROI, and hybrid intrusion decisions."""

from __future__ import annotations

from datetime import datetime
import os
import time
import uuid
from typing import Any

import cv2

from services.alert_decision_logic import AlertDecisionLogic
from services.feature_extractor import FeatureExtractor
from services.risk_utils import RiskCalculator
from services.roi_utils import ROIAnalyzer
from services.tracker import CentroidTracker


def process_video(
    video_path: str,
    detector,
    alert_service=None,
    save_dir: str = "static/results",
    frame_skip: int = 2,
    alert_cooldown_seconds: int = 60,
    save_alert_screenshots: bool = True,
    roi_detector=None,
    roi_analyzer: ROIAnalyzer | None = None,
    **_ignored,
) -> tuple[str, dict[str, Any]]:
    os.makedirs(save_dir, exist_ok=True)
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if width <= 0 or height <= 0:
        capture.release()
        raise RuntimeError("The uploaded video has invalid dimensions.")

    output_path = os.path.join(save_dir, f"{uuid.uuid4().hex}.mp4")
    writer = cv2.VideoWriter(
        output_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )
    if not writer.isOpened():
        capture.release()
        raise RuntimeError("Could not create the output video.")

    feature_extractor = FeatureExtractor()
    risk_calculator = RiskCalculator()
    alert_logic = AlertDecisionLogic()
    tracker = CentroidTracker(max_disappeared=max(10, int(fps)))

    total_frames = 0
    processed_frames = 0
    intrusion_frames = 0
    total_detections = 0
    total_roi_model_detections = 0
    inside_roi_frames = 0
    highest_confidence = 0.0
    highest_risk = 0.0
    last_alert_time = 0.0
    last_decision = alert_logic.non_intrusion()
    last_roi_summary: dict[str, Any] = {"enabled": bool(roi_detector and roi_analyzer)}

    while True:
        success, frame = capture.read()
        if not success:
            break
        total_frames += 1

        if total_frames % max(1, frame_skip) != 0:
            writer.write(frame)
            continue

        processed_frames += 1
        try:
            annotated, detections = detector.predict_frame(frame)
            enriched = feature_extractor.extract_features(detections, frame.shape)

            roi_detections: list[dict[str, Any]] = []
            if roi_analyzer:
                if roi_detector:
                    _, roi_detections = roi_detector.predict_frame(frame)
                # Manual ROI zones work independently of the optional ROI model.
                enriched, last_roi_summary = roi_analyzer.analyze(enriched, frame.shape, roi_detections)
                last_roi_summary["roi_model_loaded"] = roi_detector is not None
                total_roi_model_detections += len(roi_detections)
                if last_roi_summary.get("inside_roi_count", 0) > 0:
                    inside_roi_frames += 1
                annotated = roi_analyzer.draw_overlay(annotated, frame.shape, roi_detections)

            tracked_objects = tracker.update(enriched)
            total_detections += len(enriched)

            for detection in enriched:
                track_id = detection.get("track_id")
                track = tracked_objects.get(track_id) if track_id in tracked_objects else None
                if track:
                    detection["frames_seen"] = track["frames_seen"]
                    detection["velocity"] = track["velocity"]
                    detection["area_growth"] = track["area_growth"]
                detection.update(risk_calculator.compute_risk(detection, track, frame.shape))
                highest_confidence = max(
                    highest_confidence, float(detection.get("confidence", 0.0))
                )
                highest_risk = max(highest_risk, float(detection.get("risk_score", 0.0)))

            best_detection, risk_info = risk_calculator.select_most_dangerous(
                enriched, tracked_objects, frame.shape
            )
            if best_detection:
                combined_detection = {**best_detection, **(risk_info or {})}
                last_decision = alert_logic.decide_whether_to_alert(combined_detection)
                fuzzy_result = last_decision.get("fuzzy_result") or {}
                best_detection.update({
                    "risk_score": combined_detection.get("risk_score"),
                    "risk_level": combined_detection.get("risk_level"),
                    "fuzzy_result": last_decision.get("fuzzy_result"),
                    "fuzzy_class": fuzzy_result.get("fuzzy_class"),
                    "fuzzy_score": fuzzy_result.get("fuzzy_score"),
                    "fuzzy_risk_level": fuzzy_result.get("risk_level"),
                })
            else:
                last_decision = alert_logic.non_intrusion()

            if last_decision.get("should_alert"):
                intrusion_frames += 1
                now = time.time()
                if alert_service and now - last_alert_time >= alert_cooldown_seconds:
                    screenshot = (
                        alert_service.save_screenshot(annotated, "video_intrusion")
                        if save_alert_screenshots
                        else None
                    )
                    alert_service.send_intrusion_alert(
                        screenshot,
                        {
                            "source": "Uploaded video",
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "confidence": best_detection.get("confidence", 0),
                            "risk_score": last_decision.get("risk_score", 0),
                            "reason": last_decision.get("reason", ""),
                            "roi_status": best_detection.get("roi_status"),
                            "roi_zone": best_detection.get("roi_zone_name"),
                            "roi_context": best_detection.get("roi_context_class"),
                            "fuzzy_class": best_detection.get("fuzzy_class"),
                            "fuzzy_score": best_detection.get("fuzzy_score"),
                        },
                    )
                    last_alert_time = now
            writer.write(annotated)
        except Exception as exc:
            print(f"Video frame processing error: {exc}")
            writer.write(frame)

    capture.release()
    writer.release()

    summary = {
        "frames_total": total_frames,
        "frames_processed": processed_frames,
        "total_detections": total_detections,
        "intrusion_frames": intrusion_frames,
        "inside_roi_frames": inside_roi_frames,
        "roi_model_detections": total_roi_model_detections,
        "highest_confidence": round(highest_confidence, 6),
        "highest_risk_score": round(highest_risk, 2),
        "final_status": "intrusion" if intrusion_frames else "non_intrusion",
        "last_decision": last_decision,
        "roi_summary": last_roi_summary,
    }
    return output_path.replace("\\", "/"), summary


def record_short_clip(frames, output_path: str, fps: float = 15.0) -> str | None:
    frames = list(frames)
    if not frames:
        return None
    height, width = frames[0].shape[:2]
    writer = cv2.VideoWriter(
        output_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
    )
    if not writer.isOpened():
        return None
    for frame in frames:
        writer.write(frame)
    writer.release()
    return output_path
