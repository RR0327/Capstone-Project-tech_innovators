"""Run the application detector on one image and print extracted fields."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import argparse
import json

from services.detector import IntrusionDetector


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("--model", default="Models/best.pt")
    parser.add_argument("--conf", type=float, default=0.25)
    args = parser.parse_args()

    detector = IntrusionDetector(args.model, conf=args.conf)
    output, detections = detector.predict_image(args.image)
    print(f"Output: {output}")
    print(json.dumps(detections, indent=2))


if __name__ == "__main__":
    main()
