"""Manual OBB extraction check for a user-supplied image."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import argparse

from services.detector import IntrusionDetector


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("--model", default="Models/best.pt")
    args = parser.parse_args()
    detector = IntrusionDetector(args.model, conf=0.25)
    output, detections = detector.predict_image(args.image)
    print(f"Saved: {output}")
    print(f"Detections: {len(detections)}")
    for detection in detections:
        print(
            detection["model_class"],
            f"{detection['confidence']:.1%}",
            detection["detection_type"],
            detection["bbox"],
        )


if __name__ == "__main__":
    main()
