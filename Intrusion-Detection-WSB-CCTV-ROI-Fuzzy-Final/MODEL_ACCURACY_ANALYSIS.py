"""Print model metrics from the supplied Ultralytics results CSV."""

from __future__ import annotations

import csv
from pathlib import Path

RESULTS_PATH = Path(__file__).parent / "training" / "results.csv"


def load_rows(path: Path = RESULTS_PATH):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def as_float(row, key):
    return float(row[key])


def main() -> None:
    rows = load_rows()
    if not rows:
        raise SystemExit("No training rows found.")
    best = max(rows, key=lambda row: as_float(row, "metrics/mAP50-95(B)"))
    last = rows[-1]

    print("INTRUSION MODEL TRAINING ANALYSIS")
    print("=" * 48)
    print(f"Epochs recorded: {len(rows)}")
    print(f"Best mAP50-95 epoch: {best['epoch']}")
    print(f"Precision: {as_float(best, 'metrics/precision(B)'):.3%}")
    print(f"Recall: {as_float(best, 'metrics/recall(B)'):.3%}")
    print(f"mAP50: {as_float(best, 'metrics/mAP50(B)'):.3%}")
    print(f"mAP50-95: {as_float(best, 'metrics/mAP50-95(B)'):.3%}")
    print("\nFinal epoch losses")
    print(f"Validation box loss: {as_float(last, 'val/box_loss'):.5f}")
    print(f"Validation class loss: {as_float(last, 'val/cls_loss'):.5f}")
    print(f"Validation DFL loss: {as_float(last, 'val/dfl_loss'):.5f}")
    print(f"Validation angle loss: {as_float(last, 'val/angle_loss'):.5f}")
    print("\nNote: these are validation-run metrics, not guaranteed field accuracy.")


if __name__ == "__main__":
    main()
