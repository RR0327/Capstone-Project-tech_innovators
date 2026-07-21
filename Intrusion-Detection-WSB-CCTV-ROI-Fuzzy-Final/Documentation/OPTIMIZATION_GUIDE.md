# Optimisation Guide

## Safe starting settings

Use the defaults first:

```env
IMAGE_CONF_THRESHOLD=0.25
VIDEO_CONF_THRESHOLD=0.25
LIVE_CONF_THRESHOLD=0.30
IOU_THRESHOLD=0.40
CAMERA_FRAME_SKIP=2
```

## Reduce false alerts

Raise `LIVE_CONF_THRESHOLD` in small steps, such as 0.30 to 0.40. Keep the final alert rule separate from the detector threshold.

## Catch more weak detections

Lower the model threshold, but keep the hybrid rule. For example:

```env
LIVE_CONF_THRESHOLD=0.20
INTRUSION_REVIEW_CONFIDENCE=0.45
INTRUSION_RISK_THRESHOLD=65
MINIMUM_PERSISTENCE_FRAMES=3
```

## Improve speed

- Increase `CAMERA_FRAME_SKIP` from 2 to 3.
- Use CUDA when available.
- Keep the camera at 640×480 during early tests.
- Avoid adaptive preprocessing unless lighting causes a clear problem.

## Lighting

`ENABLE_ADAPTIVE_PREPROCESSING` is off by default because the model was trained on its own image distribution. Turn it on only after comparing results on a labelled local test set.

## Validation

Do not claim speed or accuracy gains without measuring them on the same hardware and test set. Use the training CSV only for the supplied validation metrics.
