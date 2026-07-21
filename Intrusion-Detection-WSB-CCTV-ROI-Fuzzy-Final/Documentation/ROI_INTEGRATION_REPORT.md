# ROI Integration Report

## Project Update

This updated version adds ROI / restricted-zone monitoring support to the existing hybrid intrusion detection project.

The original intrusion model remains unchanged:

```text
Models/best.pt
Models/last.pt
```

The newly supplied model files were added separately so the intrusion model is not overwritten:

```text
Models/roi_best.pt
Models/roi_last.pt
```

## ROI Model Details Found

The uploaded ROI model appears to be a YOLO OBB checkpoint. The visible class labels inside the model are:

```text
Covered Person
Normal Person
```

Because the uploaded model classes are person-context classes, not clear restricted-zone classes, the project now supports both:

```text
1. Manual ROI / restricted-zone monitoring
2. Secondary ROI/person-context model support
```

This means the project can work safely even if the ROI model is used mainly for person status rather than actual zone detection.

## New Files Added

### `services/roi_detector.py`

This file loads and runs the secondary ROI model.

It supports:

- YOLO normal bounding boxes
- YOLO OBB oriented boxes
- Class extraction
- Confidence extraction
- ROI/person-context detection drawing

### `services/roi_utils.py`

This file handles ROI logic.

It supports:

- Manual ROI zones from `.env`
- Normalized ROI coordinates
- Pixel-based ROI coordinates
- Center-inside-ROI checking
- Overlap-ratio checking
- Matching intrusion detections with ROI/person-context detections
- ROI overlay drawing

### `test_roi_logic.py`

This file tests ROI geometry and alert-gating logic.

### `test_roi_models.py`

This file checks that the new ROI model files exist.

## Updated Files

The following files were updated:

```text
OPTIMIZATION_CONFIG.py
app.py
services/alert_decision_logic.py
services/risk_utils.py
services/camera_utils.py
services/video_utils.py
templates/index.html
templates/result.html
templates/live_camera.html
static/js/camera.js
.env.example
.env.template
README.md
system_design.md
workflow.md
explanation.md
PROJECT_DEFENCE_REPORT.md
FINAL_COMPLETION_REPORT.md
```

## New Environment Settings

```env
ENABLE_ROI_MONITORING=true
ROI_MODEL_PATH=Models/roi_best.pt
ROI_MODE=HYBRID
ROI_CONF_THRESHOLD=0.25
ROI_IOU_THRESHOLD=0.40
ROI_MAX_DETECTIONS=100
REQUIRE_ROI_FOR_ALERT=false
ROI_MIN_OVERLAP_RATIO=0.10
ROI_USE_CENTER_CHECK=true
ROI_ZONE_CLASSES=restricted_zone,restricted area,roi,zone
ROI_ALERT_CONTEXT_CLASSES=covered person,covered_person
ROI_MANUAL_ZONES=
```

## Manual ROI Example

Use normalized coordinates from `0` to `1`:

```env
ROI_MANUAL_ZONES=[{"name":"cash_counter","x1":0.45,"y1":0.20,"x2":0.95,"y2":0.95}]
```

This means:

```text
x1 = 45% from left
 y1 = 20% from top
x2 = 95% from left
 y2 = 95% from top
```

## Alert Logic After ROI Update

The current default is safe and backward-compatible:

```env
REQUIRE_ROI_FOR_ALERT=false
```

This means:

```text
Intrusion detected anywhere
    -> Normal intrusion alert rules still work

ROI detected or covered-person context found
    -> Adds extra risk/context
```

If stricter ROI monitoring is needed, set:

```env
REQUIRE_ROI_FOR_ALERT=true
```

Then the system follows this rule:

```text
Intrusion inside ROI
    -> Alert allowed

Intrusion outside ROI
    -> Alert blocked
```

The system can also support ROI model context:

```text
Covered Person detected by ROI model
    -> Adds ROI/person-context support
    -> Adds risk bonus
```

## Updated Workflow

```text
Image / Video / Live Camera
        |
        v
Primary intrusion model
        |
        v
Secondary ROI/person-context model
        |
        v
Manual ROI zone check
        |
        v
Inside/outside ROI decision
        |
        v
Hybrid risk calculation
        |
        v
Final alert decision
        |
        v
Evidence saving and email alert
```

## Test Result

The updated project passed the available safe test suite in this environment:

```text
34 passed
2 skipped
0 failed
```

The two skipped tests are live-email tests and should only run when explicit live-email permission is enabled.

## Important Notes

1. The original intrusion model was not replaced.
2. The uploaded model was added as a secondary ROI model.
3. ROI model labels found: `Covered Person`, `Normal Person`.
4. Manual ROI zones are supported through `.env`.
5. ROI-required alert gating is optional and controlled by `REQUIRE_ROI_FOR_ALERT`.
6. The private `.env` file is not included in the final ZIP.
7. Real camera and real email testing still require the user's local environment and fresh private credentials.
