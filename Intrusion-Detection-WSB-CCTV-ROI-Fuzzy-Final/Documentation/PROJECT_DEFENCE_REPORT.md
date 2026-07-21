# Project Defence Report

## Title

**A Hybrid Computer Vision Intrusion and Non-Intrusion Detection System for Homes and Retail Shops**

## Problem

Homes and retail shops often depend on people watching CCTV screens. Human monitoring can miss short events, especially when many cameras run at once. This project automates the first screening step by finding visual patterns labelled as intrusion and sending an alert when the evidence is strong.

## Objective

The first stage aims to:

1. Detect intrusion from images, recorded video, and a live camera.
2. Report non-intrusion when no valid intrusion is found.
3. Reduce weak one-frame alerts through tracking and risk rules.
4. Save visual evidence and send an optional email alert.
5. Prepare the design for later night-vision and ROI modules.

## Model

The supplied checkpoint is a YOLOv8n oriented-bounding-box model. It has one class: `intrusion`. Therefore, non-intrusion is an application decision based on the absence of a valid intrusion result, not a second neural-network class.

Training settings from `training/args.yaml`:

- Task: OBB detection
- Epochs: 15
- Batch size: 16
- Image size: 640
- Pretrained base model: `yolov8n-obb.pt`
- Validation enabled

## Validation results

The last row of the supplied CSV records:

| Metric | Value |
|---|---:|
| Precision | 98.508% |
| Recall | 97.248% |
| mAP50 | 98.353% |
| mAP50–95 | 89.419% |

The same epoch has the highest supplied mAP50–95. These values describe the supplied validation set only. Field testing is still required for new homes, shops, camera angles, clothing, lighting, and occlusion.

## Hybrid computer vision design

The system is hybrid because the neural model is not the only decision source.

1. **YOLOv8 OBB:** finds intrusion regions and confidence values.
2. **Spatial features:** measures box area, centre, and border proximity.
3. **Tracking:** estimates persistence, movement, and box growth across frames.
4. **Risk score:** combines confidence, area, persistence, and motion.
5. **Decision rules:** high confidence can alert at once; medium confidence needs supporting risk and persistence.

## Input modes

- Image upload: one-frame detection and decision
- Video upload: frame processing with tracking and annotated output
- Live camera: continuous detection, tracking, dashboard updates, and cooldown-based alerts

## Alert rule

Default rules:

- Confidence at or above 80%: alert
- Confidence from 45% to 80%: alert only when risk is at least 65 and the object persists for at least three processed frames
- No valid detection: non-intrusion

All thresholds are configurable through `.env`.

## Limitations

- The model is one-class, so it does not identify authorised people by identity.
- “Non-intrusion” means no qualifying intrusion detection, not proof that the scene is safe.
- The current stage does not include night vision or ROI permission rules.
- Email delivery depends on SMTP configuration and network access.
- Camera performance changes with lighting, distance, occlusion, and hardware.

## Future work

1. Add low-light and infrared support.
2. Add user-defined ROI polygons and restricted-zone entry rules.
3. Add authorised-person recognition only with clear consent and privacy controls.
4. Measure false positives and false negatives on real home and shop CCTV.
5. Add event storage, audit logs, and a dashboard history page.

---

# ROI Enhancement for Final Defence

A new ROI/person-context module has been added to the project. The original intrusion model still detects the class `intrusion`. The new secondary model is stored separately as `Models/roi_best.pt` and `Models/roi_last.pt`.

The visible classes in the uploaded secondary model are:

```text
Covered Person
Normal Person
```

The system now supports manual ROI monitoring, secondary ROI model context, and optional ROI-required alert gating. This improves the project because the system can focus on important restricted areas rather than treating the whole camera frame equally.

Example defence explanation:

```text
The primary YOLOv8 OBB model detects intrusion candidates. Then the ROI module checks whether the detected object is inside a restricted zone or supported by ROI/person-context evidence. Finally, the risk calculator and alert-decision logic decide whether an alert should be sent.
```
