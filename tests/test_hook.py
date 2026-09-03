from pathlib import Path
from igt_fus_auditory.hook import validate_hook


def test_mock_hook_shape():
    root = Path(__file__).resolve().parents[1]
    result = validate_hook(root / "examples" / "mock_fus_hook.py")
    assert result["prepare"] and result["execute"]
