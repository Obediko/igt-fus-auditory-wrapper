import numpy as np
from igt_fus_auditory.config import MaskConfig
from igt_fus_auditory.signals import generate_mask


def test_deterministic_mask():
    cfg = MaskConfig(stimulation_duration_s=1, pre_mask_s=0, post_mask_s=0)
    a = generate_mask(cfg)
    b = generate_mask(cfg)
    assert np.array_equal(a.audio, b.audio)
    assert a.audio.shape[1] == 2
    assert a.peak <= 1.0
