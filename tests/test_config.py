import pytest
from igt_fus_auditory.config import MaskConfig


def test_default_config_is_valid():
    cfg = MaskConfig().validate()
    assert cfg.expected_pulses == 450
    assert cfg.pulse_interval_ms == pytest.approx(200.0)


def test_audio_ramp_must_fit_gate():
    with pytest.raises(ValueError):
        MaskConfig(matched_pulse_width_ms=20, audio_ramp_ms=11).validate()
