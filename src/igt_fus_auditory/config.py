from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Any

SUPPORTED_PROFILES = (
    "simple_prf",
    "matched_plus_white",
    "matched_plus_pink",
    "matched_plus_narrowband",
    "auditory_mondrian",
)


@dataclass(frozen=True)
class MaskConfig:
    """Auditory-mask settings only.

    Nothing in this object configures an ultrasound generator, transducer,
    calibration file, conversion file, pressure, steering, or sonication ramp.
    `matched_pulse_width_ms` describes the audible matching gate only.
    """

    protocol_label: str = "study-mask"
    stimulation_duration_s: float = 90.0
    prf_hz: float = 5.0
    matched_pulse_width_ms: float = 20.0
    pre_mask_s: float = 1.0
    post_mask_s: float = 1.0
    sample_rate_hz: int = 48000
    carrier_hz: float = 14000.0
    profile: str = "simple_prf"
    matching_gain: float = 0.35
    background_gain: float = 0.30
    master_gain: float = 0.80
    audio_ramp_ms: float = 5.0
    stereo_pan: float = 0.0
    random_seed: int = 20260903
    narrowband_center_hz: float = 1000.0
    narrowband_bandwidth_hz: float = 400.0
    mondrian_density_per_s: float = 6.0
    mondrian_tone_ms: float = 300.0
    output_device: str | int | None = None
    headphones_calibrated: bool = False

    @property
    def total_duration_s(self) -> float:
        return self.pre_mask_s + self.stimulation_duration_s + self.post_mask_s

    @property
    def pulse_interval_ms(self) -> float:
        return 1000.0 / self.prf_hz

    @property
    def expected_pulses(self) -> int:
        return int(round(self.stimulation_duration_s * self.prf_hz))

    def validate(self) -> "MaskConfig":
        for name, value in (
            ("stimulation_duration_s", self.stimulation_duration_s),
            ("prf_hz", self.prf_hz),
            ("matched_pulse_width_ms", self.matched_pulse_width_ms),
            ("carrier_hz", self.carrier_hz),
        ):
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be a finite positive number")
        if self.profile not in SUPPORTED_PROFILES:
            raise ValueError(f"profile must be one of {SUPPORTED_PROFILES}")
        if self.sample_rate_hz < 16000:
            raise ValueError("sample_rate_hz must be at least 16000")
        if self.carrier_hz >= self.sample_rate_hz / 2:
            raise ValueError("carrier_hz must be below Nyquist")
        if self.matched_pulse_width_ms > self.pulse_interval_ms:
            raise ValueError("matched_pulse_width_ms cannot exceed the PRF interval")
        if self.audio_ramp_ms < 0 or self.audio_ramp_ms * 2 > self.matched_pulse_width_ms:
            raise ValueError("audio_ramp_ms must fit inside the audible matching gate")
        if self.pre_mask_s < 0 or self.post_mask_s < 0:
            raise ValueError("pre/post mask durations cannot be negative")
        for name, value in (
            ("matching_gain", self.matching_gain),
            ("background_gain", self.background_gain),
            ("master_gain", self.master_gain),
        ):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if not -1 <= self.stereo_pan <= 1:
            raise ValueError("stereo_pan must be between -1 and 1")
        if not 0 <= int(self.random_seed) <= 2**32 - 1:
            raise ValueError("random_seed must fit uint32")
        return self

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, path: str | Path) -> "MaskConfig":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**data).validate()

    def to_json(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")
        return target
