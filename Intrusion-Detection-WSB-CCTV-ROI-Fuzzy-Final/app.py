"""Flask entry point for the hybrid intrusion + ROI monitoring system."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import cv2
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request
from werkzeug.utils import secure_filename

load_dotenv()

from OPTIMIZATION_CONFIG import ALERT, CAMERA, DETECTION, ROI
from services.alert_decision_logic import AlertDecisionLogic
from services.alert_service import AlertService
from services.camera_utils import CameraStream
from services.detector import IntrusionDetector
from services.feature_extractor import FeatureExtractor
from services.risk_utils import RiskCalculator
from services.roi_detector import ROIDetector
from services.roi_utils import ROIAnalyzer
from services.video_utils import process_video

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
RESULT_DIR = BASE_DIR / "static" / "results"
ALERT_DIR = BASE_DIR / "static" / "alerts"
for directory in (UPLOAD_DIR, RESULT_DIR, ALERT_DIR):
    directory.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_MB", "200")) * 1024 * 1024

_configured_model_path = Path(os.getenv("MODEL_PATH", "Models/best.pt"))
MODEL_PATH = str(
    _configured_model_path
    if _configured_model_path.is_absolute()
    else BASE_DIR / _configured_model_path
)

_configured_roi_model_path = Path(ROI.model_path)
ROI_MODEL_PATH = str(
    _configured_roi_model_path
    if _configured_roi_model_path.is_absolute()
    else BASE_DIR / _configured_roi_model_path
)


def _make_detector(confidence: float) -> IntrusionDetector:
    return IntrusionDetector(
        model_path=MODEL_PATH,
        conf=confidence,
        iou=DETECTION.iou,
        adaptive_preprocessing=DETECTION.adaptive_preprocessing,
        max_det=DETECTION.max_detections,
    )


def _make_roi_detector() -> ROIDetector | None:
    if not ROI.enabled:
        return None
    if not Path(ROI_MODEL_PATH).exists():
        return None
    return ROIDetector(
        model_path=ROI_MODEL_PATH,
        conf=ROI.conf,
        iou=ROI.iou,
        max_det=ROI.max_detections,
    )


detector_image = _make_detector(DETECTION.image_conf)
detector_video = _make_detector(DETECTION.video_conf)
detector_live = _make_detector(DETECTION.live_conf)
roi_detector = _make_roi_detector()
roi_analyzer = ROIAnalyzer.from_config(ROI)
feature_extractor = FeatureExtractor()
risk_calculator = RiskCalculator()
alert_logic = AlertDecisionLogic()
alert_service = AlertService()
camera_stream: CameraStream | None = None


def _save_upload(file_storage, folder: Path, allowed: set[str]) -> str:
    original = secure_filename(file_storage.filename or "")
    extension = Path(original).suffix.lower()
    if extension not in allowed:
        raise ValueError(f"Unsupported file type: {extension or 'unknown'}")
    filename = f"{uuid.uuid4().hex}{extension}"
    path = folder / filename
    file_storage.save(path)
    return str(path)


def _web_path(file_path: str) -> str:
    return str(Path(file_path).resolve().relative_to(BASE_DIR)).replace("\\", "/")


def _apply_roi_to_image(
    original_image,
    annotated_path: str,
    enriched: list[dict],
) -> tuple[list[dict], dict, list[dict]]:
    if original_image is None:
        return enriched, {"enabled": False, "reason": "Original image unavailable."}, []
    if not ROI.enabled:
        return enriched, {
            "enabled": False,
            "roi_model_loaded": False,
            "reason": "ROI monitoring is disabled.",
            "require_roi_for_alert": False,
        }, []

    roi_detections = []
    if roi_detector is not None:
        _, roi_detections = roi_detector.predict_frame(original_image)

    # Manual ROI zones remain active even when the optional ROI model is absent.
    enriched, roi_summary = roi_analyzer.analyze(enriched, original_image.shape, roi_detections)
    roi_summary["roi_model_loaded"] = roi_detector is not None
    roi_summary["model_path"] = ROI_MODEL_PATH if roi_detector is not None else None

    annotated = cv2.imread(annotated_path)
    if annotated is not None:
        annotated = roi_analyzer.draw_overlay(annotated, original_image.shape, roi_detections)
        cv2.imwrite(annotated_path, annotated)
    return enriched, roi_summary, roi_detections


@app.get("/")
def home():
    return render_template(
        "index.html",
        model_info=detector_image.model_info(),
        roi_model_info=roi_detector.model_info() if roi_detector else None,
        roi_enabled=ROI.enabled,
    )


@app.post("/detect-image")
def detect_image():
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return "Please choose an image.", 400
    try:
        image_path = _save_upload(uploaded, UPLOAD_DIR, ALLOWED_IMAGE_EXTENSIONS)
        output_path, detections = detector_image.predict_image(
            image_path, save_dir=str(RESULT_DIR)
        )
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        return str(exc), 400

    image = cv2.imread(image_path)
    enriched = feature_extractor.extract_features(
        detections, image.shape if image is not None else None
    )
    enriched, roi_summary, roi_detections = _apply_roi_to_image(image, output_path, enriched)

    best_detection, risk_info = risk_calculator.select_most_dangerous(
        enriched, frame_shape=image.shape if image is not None else None
    )
    if best_detection:
        combined_detection = {**best_detection, **(risk_info or {})}
        decision = alert_logic.decide_whether_to_alert(combined_detection)
        best_detection.update({
            "risk_score": combined_detection.get("risk_score"),
            "risk_level": combined_detection.get("risk_level"),
            "fuzzy_result": decision.get("fuzzy_result"),
            "fuzzy_class": (decision.get("fuzzy_result") or {}).get("fuzzy_class"),
            "fuzzy_score": (decision.get("fuzzy_result") or {}).get("fuzzy_score"),
            "fuzzy_risk_level": (decision.get("fuzzy_result") or {}).get("risk_level"),
        })
    else:
        decision = alert_logic.non_intrusion()

    if decision.get("should_alert"):
        alert_service.send_intrusion_alert(
            output_path,
            {
                "confidence": best_detection.get("confidence", 0),
                "risk_score": decision.get("risk_score", 0),
                "reason": decision.get("reason", ""),
                "roi_status": best_detection.get("roi_status"),
                "roi_zone": best_detection.get("roi_zone_name"),
                "roi_context": best_detection.get("roi_context_class"),
                "fuzzy_class": best_detection.get("fuzzy_class"),
                "fuzzy_score": best_detection.get("fuzzy_score"),
            },
        )

    return render_template(
        "result.html",
        kind="image",
        output_path=_web_path(output_path),
        detections=enriched,
        roi_detections=roi_detections,
        roi_summary=roi_summary,
        decision=decision,
    )


@app.post("/detect-video")
def detect_video():
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return "Please choose a video.", 400
    try:
        video_path = _save_upload(uploaded, UPLOAD_DIR, ALLOWED_VIDEO_EXTENSIONS)
        output_path, summary = process_video(
            video_path,
            detector_video,
            alert_service=alert_service,
            save_dir=str(RESULT_DIR),
            frame_skip=DETECTION.video_frame_skip,
            alert_cooldown_seconds=ALERT.cooldown_seconds,
            save_alert_screenshots=ALERT.save_screenshots,
            roi_detector=roi_detector,
            roi_analyzer=roi_analyzer,
        )
    except (ValueError, RuntimeError) as exc:
        return str(exc), 400
    return render_template(
        "result.html",
        kind="video",
        output_path=_web_path(output_path),
        summary=summary,
        roi_summary=summary.get("roi_summary"),
        decision=summary.get("last_decision"),
    )


@app.get("/live-camera")
def live_camera_page():
    return render_template("live_camera.html", roi_enabled=ROI.enabled)


@app.post("/start-camera")
def start_camera():
    global camera_stream
    payload = request.get_json(silent=True) or {}
    flip_camera = bool(payload.get("flip_camera", CAMERA.flip_camera))
    try:
        if camera_stream is None:
            camera_stream = CameraStream(
                detector=detector_live,
                camera_index=CAMERA.camera_index,
                alert_service=alert_service,
                cooldown_seconds=ALERT.cooldown_seconds,
                frame_skip=CAMERA.frame_skip,
                use_flipped_camera=flip_camera,
                save_alert_screenshots=ALERT.save_screenshots,
                roi_detector=roi_detector,
                roi_analyzer=roi_analyzer,
            )
        camera_stream.start()
        return jsonify({"status": "success", "message": "Camera started."})
    except Exception as exc:
        camera_stream = None
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.post("/stop-camera")
def stop_camera():
    global camera_stream
    if camera_stream is not None:
        camera_stream.stop()
        camera_stream = None
    return jsonify({"status": "success", "message": "Camera stopped."})


def _generate_frames():
    while camera_stream is not None and camera_stream.running:
        frame = camera_stream.get_frame()
        if frame is None:
            continue
        encoded = camera_stream.encode_frame(frame)
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + encoded + b"\r\n"


@app.get("/video-feed")
def video_feed():
    return Response(
        _generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/get-detections")
def get_detections():
    if camera_stream is None:
        return jsonify(
            {
                "count": 0,
                "detections": [],
                "status": "camera_stopped",
                "decision": alert_logic.non_intrusion("Camera is not running."),
                "roi_summary": {"enabled": ROI.enabled, "camera_running": False},
            }
        )
    return jsonify(camera_stream.get_detections())


@app.get("/api/model-info")
def model_info():
    return jsonify(
        {
            "intrusion_model": detector_image.model_info(),
            "roi_model": roi_detector.model_info() if roi_detector else None,
            "roi_enabled": ROI.enabled,
            "roi_require_for_alert": ROI.require_roi_for_alert,
        }
    )


@app.get("/api/email-trigger-status")
def email_trigger_status():
    return jsonify(alert_service.get_trigger_status())


@app.get("/api/email-trigger-modes")
def email_trigger_modes():
    return jsonify(
        {
            "current_mode": alert_service.email_trigger_mode,
            "available_modes": {
                "ALWAYS": "Send every intrusion alert.",
                "COOLDOWN_60": "Send at most one email each minute.",
                "COOLDOWN_300": "Send at most one email every five minutes.",
                "COOLDOWN_3600": "Send at most one email each hour.",
                "MANUAL": "Do not send automatic emails.",
            },
        }
    )


@app.post("/api/email-trigger-set")
def email_trigger_set():
    payload = request.get_json(silent=True) or {}
    result = alert_service.set_trigger_mode(payload.get("mode", ""))
    return jsonify(result), 200 if result.get("success") else 400


@app.errorhandler(413)
def upload_too_large(_error):
    return "The uploaded file is larger than the configured limit.", 413


if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
        threaded=True,
    )
