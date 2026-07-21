"""Verify source files, model checkpoints, and training evidence."""

from __future__ import annotations

import csv
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def checkpoint_root(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
    if not names:
        raise ValueError(f"Checkpoint archive is empty: {path}")
    return names[0].split("/")[0]


def main() -> None:
    required_source = [
        ROOT / "app.py",
        ROOT / "OPTIMIZATION_CONFIG.py",
        ROOT / "requirements.txt",
        ROOT / "services" / "detector.py",
        ROOT / "services" / "roi_utils.py",
        ROOT / "services" / "fuzzy_logic.py",
        ROOT / "templates" / "index.html",
        ROOT / "static" / "css" / "style.css",
        ROOT / "training" / "args.yaml",
        ROOT / "training" / "results.csv",
    ]
    missing_source = [path.relative_to(ROOT) for path in required_source if not path.exists()]
    if missing_source:
        print("Missing source files:")
        for path in missing_source:
            print(f"  - {path}")
        raise SystemExit(1)

    checkpoints = {
        "best": ROOT / "Models" / "best.pt",
        "last": ROOT / "Models" / "last.pt",
        "roi_best": ROOT / "Models" / "roi_best.pt",
        "roi_last": ROOT / "Models" / "roi_last.pt",
    }
    missing_models = [path.relative_to(ROOT) for path in checkpoints.values() if not path.exists()]
    if missing_models:
        print("Source structure passed, but model files are missing:")
        for path in missing_models:
            print(f"  - {path}")
        print("Copy the original trained .pt files into Models/ and run this command again.")
        raise SystemExit(2)

    with (ROOT / "training" / "results.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit("training/results.csv contains no rows.")
    best_row = max(rows, key=lambda row: float(row["metrics/mAP50-95(B)"]))

    print("Project verification passed.")
    for label, path in checkpoints.items():
        print(f"{path.name} archive label: {checkpoint_root(path)}")
    print(f"Best supplied epoch: {best_row['epoch']}")
    print(f"Best supplied mAP50-95: {float(best_row['metrics/mAP50-95(B)']):.3%}")


if __name__ == "__main__":
    main()
