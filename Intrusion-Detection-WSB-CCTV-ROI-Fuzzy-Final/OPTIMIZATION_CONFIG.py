"""Central configuration for the intrusion-detection application."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    return default if value is None else value.strip()


@dataclass(frozen=True)
class DetectionConfig:
    image_conf: float = _env_float("IMAGE_CONF_THRESHOLD", 0.25)
    video_conf: float = _env_float("VIDEO_CONF_THRESHOLD", 0.25)
    live_conf: float = _env_float("LIVE_CONF_THRESHOLD", 0.30)
    iou: float = _env_float("IOU_THRESHOLD", 0.40)
    max_detections: int = _env_int("MAX_DETECTIONS", 100)
    adaptive_preprocessing: bool = _env_bool("ENABLE_ADAPTIVE_PREPROCESSING", False)
    video_frame_skip: int = max(1, _env_int("VIDEO_FRAME_SKIP", 2))


@dataclass(frozen=True)
class ROIConfig:
    """Settings for restricted-zone / ROI monitoring.

    The uploaded secondary model is stored as Models/roi_best.pt. The model
    is used as a context/person-type model. It may detect classes such as abnormal person, covered person, normal person, weapon, or background. Manual ROI zones are
    still supported through ROI_MANUAL_ZONES.
    """

    enabled: bool = _env_bool("ENABLE_ROI_MONITORING", True)
    model_path: str = _env_str("ROI_MODEL_PATH", "Models/roi_best.pt")
    conf: float = _env_float("ROI_CONF_THRESHOLD", 0.25)
    iou: float = _env_float("ROI_IOU_THRESHOLD", 0.40)
    max_detections: int = _env_int("ROI_MAX_DETECTIONS", 100)
    mode: str = _env_str("ROI_MODE", "HYBRID").upper()
    require_roi_for_alert: bool = _env_bool("REQUIRE_ROI_FOR_ALERT", True)
    manual_zones_json: str = _env_str("ROI_MANUAL_ZONES", "")
    min_overlap_ratio: float = _env_float("ROI_MIN_OVERLAP_RATIO", 0.10)
    use_center_check: bool = _env_bool("ROI_USE_CENTER_CHECK", True)
    zone_class_names: str = _env_str(
        "ROI_ZONE_CLASSES", "restricted_zone,restricted area,roi,zone"
    )
    alert_context_classes: str = _env_str(
        "ROI_ALERT_CONTEXT_CLASSES", "abnormal person,covered person,normal person,weapon,background,covered_person,normal_person"
    )


@dataclass(frozen=True)
class DecisionConfig:
    high_confidence: float = _env_float("INTRUSION_HIGH_CONFIDENCE", 0.80)
    review_confidence: float = _env_float("INTRUSION_REVIEW_CONFIDENCE", 0.45)
    risk_threshold: float = _env_float("INTRUSION_RISK_THRESHOLD", 65.0)
    minimum_persistence_frames: int = _env_int("MINIMUM_PERSISTENCE_FRAMES", 3)
    require_roi_for_alert: bool = _env_bool("REQUIRE_ROI_FOR_ALERT", True)


@dataclass(frozen=True)
class CameraConfig:
    camera_index: int = _env_int("CAMERA_INDEX", 0)
    width: int = _env_int("CAMERA_WIDTH", 640)
    height: int = _env_int("CAMERA_HEIGHT", 480)
    fps: int = _env_int("CAMERA_FPS", 30)
    frame_skip: int = max(1, _env_int("CAMERA_FRAME_SKIP", 2))
    jpeg_quality: int = min(95, max(40, _env_int("JPEG_QUALITY", 78)))
    flip_camera: bool = _env_bool("FLIP_CAMERA", False)


@dataclass(frozen=True)
class AlertConfig:
    cooldown_seconds: int = max(0, _env_int("ALERT_COOLDOWN_SECONDS", 60))
    save_screenshots: bool = _env_bool("SAVE_ALERT_SCREENSHOTS", True)
    email_trigger_mode: str = os.getenv("EMAIL_TRIGGER_MODE", "COOLDOWN_60").upper()


DETECTION = DetectionConfig()
ROI = ROIConfig()
DECISION = DecisionConfig()
CAMERA = CameraConfig()
ALERT = AlertConfig()
