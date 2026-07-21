"""Compare current intrusion-model detections at two thresholds."""


from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse

from services.detector import IntrusionDetector


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("--low", type=float, default=0.20)
    parser.add_argument("--high", type=float, default=0.40)
    args = parser.parse_args()
    for threshold in (args.low, args.high):
        detector = IntrusionDetector("Models/best.pt", conf=threshold)
        _, detections = detector.predict_image(args.image)
        print(f"Threshold {threshold:.2f}: {len(detections)} detections")
        for detection in detections:
            print(f"  intrusion {detection['confidence']:.1%}")


if __name__ == "__main__":
    main()
