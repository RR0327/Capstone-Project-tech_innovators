"""Inspect the supplied YOLO checkpoint and one optional image."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import argparse
from pathlib import Path



def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Models/best.pt")
    parser.add_argument("--image")
    parser.add_argument("--conf", type=float, default=0.25)
    args = parser.parse_args()

    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit(
            "Ultralytics is not installed. Run: pip install -r requirements.txt"
        ) from exc

    model = YOLO(args.model)
    print(f"Task: {model.task}")
    print(f"Classes: {model.names}")
    if not args.image:
        return
    if not Path(args.image).exists():
        raise SystemExit(f"Image not found: {args.image}")
    result = model.predict(args.image, conf=args.conf, verbose=False)[0]
    boxes = result.boxes
    obb = result.obb
    print(f"Regular boxes: {0 if boxes is None else len(boxes)}")
    print(f"Oriented boxes: {0 if obb is None else len(obb)}")


if __name__ == "__main__":
    main()
