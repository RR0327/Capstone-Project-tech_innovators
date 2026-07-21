"""Manual image test: python test_recent_img.py path/to/image.jpg"""


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
    args = parser.parse_args()
    output, detections = IntrusionDetector("Models/best.pt").predict_image(args.image)
    print(output)
    print(detections)


if __name__ == "__main__":
    main()
