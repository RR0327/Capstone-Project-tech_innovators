# ROI + Fuzzy Logic Modification Report

## Final Correct Workflow

The updated project now follows the workflow requested by the user:

```text
Input Image / Video / Live Camera
        |
        v
Primary Intrusion Detection Model
        |
        v
Is intrusion detected?
        |
   +----+----+
   |         |
  No        Yes
   |         |
   v         v
No alert   Get intrusion bounding box
                |
                v
        Check bounding box with restricted ROI area
                |
                v
        Did bounding box enter ROI?
                |
          +-----+-----+
          |           |
         No          Yes
          |           |
          v           v
   No ROI alert   Send ROI intrusion data to fuzzy logic
                        |
                        v
        Fuzzy logic checks detected class/person type
                        |
                        v
        abnormal person / covered person / normal person / weapon / background
                        |
                        v
              Final alert decision
```

## Important Meaning

The system does **not** alert only because a person exists in the frame.

The system also does **not** run fuzzy logic before intrusion detection.

The correct order is:

1. The primary model checks whether intrusion exists.
2. If there is no intrusion, the system gives no alert.
3. If intrusion exists, the system extracts the intrusion bounding box.
4. The system checks whether the intrusion bounding box enters the restricted ROI area.
5. If the intrusion bounding box does not enter ROI, the system gives no ROI alert.
6. If the intrusion bounding box enters ROI, the ROI/person-context model result goes to fuzzy logic.
7. Fuzzy logic checks class/person type.
8. Final alert decision is made.

## Files Added or Modified

### Added

```text
services/fuzzy_logic.py
ROI_FUZZY_MODIFICATION_REPORT.md
test_fuzzy_logic.py
```

### Modified

```text
services/alert_decision_logic.py
services/roi_utils.py
services/camera_utils.py
services/video_utils.py
services/decision_engine.py
app.py
static/js/camera.js
templates/result.html
templates/live_camera.html
OPTIMIZATION_CONFIG.py
.env.example
.env.template
test_intrusion_logic.py
test_roi_logic.py
test_full_system.py
test_camera_pipeline.py
test_decision_engine.py
test_conf_threshold.py
test_alert_system.py
test_image_alert.py
```

## New Fuzzy Logic File

### `services/fuzzy_logic.py`

This file performs the final fuzzy decision after intrusion and ROI checks.

It uses these inputs:

```text
intrusion_confidence
roi_overlap_ratio
bbox_area_ratio
previous risk score
roi/person-context class
class confidence
```

It supports these fuzzy classes:

```text
abnormal person
covered person
normal person
weapon
background
unknown/other
```

## Fuzzy Decision Meaning

| Fuzzy Class | Final Meaning |
|---|---|
| weapon | Critical ROI intrusion alert |
| abnormal person | High-risk ROI intrusion alert |
| covered person | High-risk ROI intrusion alert |
| normal person | Usually no alert unless fuzzy score is very high |
| background | No alert |
| unknown/other | Alert only if fuzzy score is high enough |

## Decision Examples

### Case 1: No Intrusion

```text
Primary model result: no intrusion
Final output: no alert
```

### Case 2: Intrusion Outside ROI

```text
Primary model result: intrusion
ROI result: bounding box outside restricted area
Final output: no ROI intrusion alert
```

### Case 3: Covered Person Inside ROI

```text
Primary model result: intrusion
ROI result: bounding box entered restricted area
Fuzzy class: covered person
Final output: high-risk ROI intrusion alert
```

### Case 4: Weapon Inside ROI

```text
Primary model result: intrusion
ROI result: bounding box entered restricted area
Fuzzy class: weapon
Final output: critical ROI intrusion alert
```

### Case 5: Normal Person Inside ROI

```text
Primary model result: intrusion
ROI result: bounding box entered restricted area
Fuzzy class: normal person
Final output: normally no alert / low-risk event
```

## Configuration

The ROI workflow is controlled from `.env`.

Important settings:

```env
ENABLE_ROI_MONITORING=true
ROI_MODEL_PATH=Models/roi_best.pt
REQUIRE_ROI_FOR_ALERT=true
ROI_MIN_OVERLAP_RATIO=0.10
ROI_USE_CENTER_CHECK=true
ROI_MANUAL_ZONES=[{"name":"restricted_area","bbox":[0.35,0.20,0.95,0.95]}]
```

### ROI Manual Zone Format

The default example uses normalized coordinates.

```text
x1, y1, x2, y2
```

Each value is between `0` and `1`.

Example:

```env
ROI_MANUAL_ZONES=[{"name":"cash_counter","bbox":[0.45,0.20,0.95,0.95]}]
```

This means:

```text
Restricted area starts around 45% from the left side
and 20% from the top side of the frame.
```

## Final Alert Rule

The new final alert rule is:

```text
Alert = intrusion detected + bounding box entered ROI + fuzzy logic confirms suspicious class
```

The system does not send an ROI alert when:

```text
No intrusion is detected
Intrusion is outside ROI
Fuzzy class is background
Fuzzy class is normal person with low fuzzy score
```

## Test Result

The updated project tests passed:

```text
39 passed
2 skipped
0 failed
```

The skipped tests are live-email tests that require explicit permission and real private email credentials.

## Defence Explanation

You can explain the updated ROI part like this:

```text
The system first uses the primary YOLO intrusion model to check whether an intrusion event exists. If the model does not detect intrusion, no alert is generated. When intrusion is detected, the system extracts the intrusion bounding box and checks whether that box enters a restricted Region of Interest. If the box does not enter the ROI, the system does not generate an ROI alert. If it enters the ROI, the ROI/person-context model output is passed to a fuzzy logic module. The fuzzy logic evaluates classes such as abnormal person, covered person, normal person, weapon, or background and produces the final alert decision.
```

## Current Practical Note

The restricted ROI area is currently configured through `.env` using `ROI_MANUAL_ZONES`. For a future version, a browser-based ROI drawing interface can be added so the user can draw the restricted area directly on the live camera page.
