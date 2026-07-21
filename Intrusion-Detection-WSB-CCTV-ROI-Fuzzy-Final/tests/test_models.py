from pathlib import Path
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "Models"
BEST = MODELS / "best.pt"
LAST = MODELS / "last.pt"


def _require_models():
    if not BEST.is_file() or not LAST.is_file():
        pytest.skip("Add Models/best.pt and Models/last.pt to run checkpoint tests.")


def test_best_and_last_checkpoints_are_present():
    _require_models()
    assert BEST.is_file()
    assert LAST.is_file()


def test_checkpoint_archive_labels_match_filenames():
    _require_models()
    with zipfile.ZipFile(BEST) as archive:
        assert archive.namelist()[0].startswith("best/")
    with zipfile.ZipFile(LAST) as archive:
        assert archive.namelist()[0].startswith("last/")
