from pathlib import Path
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "Models"
BEST = MODELS / "roi_best.pt"
LAST = MODELS / "roi_last.pt"


def _require_models():
    if not BEST.is_file() or not LAST.is_file():
        pytest.skip("Add Models/roi_best.pt and Models/roi_last.pt to run ROI checkpoint tests.")


def test_roi_model_files_are_present():
    _require_models()
    assert BEST.is_file()
    assert LAST.is_file()


def test_roi_checkpoints_match_uploaded_archive_names():
    _require_models()
    with zipfile.ZipFile(BEST) as archive:
        assert archive.namelist()[0].startswith("best/")
    with zipfile.ZipFile(LAST) as archive:
        assert archive.namelist()[0].startswith("last/")
