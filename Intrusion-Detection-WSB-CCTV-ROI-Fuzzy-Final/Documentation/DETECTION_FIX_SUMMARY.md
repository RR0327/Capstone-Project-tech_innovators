# OBB Detection Extraction Fix

The supplied model uses an oriented-bounding-box head. Ultralytics places these detections in `result.obb`, while standard object-detection models use `result.boxes`.

The updated `services/detector.py` supports both formats. For OBB results it stores:

- an axis-aligned `bbox` for tracking and area calculations
- the four-point `polygon` for accurate drawing
- confidence, class, centre, and area values

This prevents the old problem where an annotated result appeared on screen but the application returned an empty detection list.
