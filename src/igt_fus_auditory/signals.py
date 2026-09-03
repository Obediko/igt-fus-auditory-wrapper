from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from scipy.signal import butter, sosfiltfilt

from .config import MaskConfig


@dataclass(frozen=True)
class GeneratedMask:
    audio: np.ndarray
    sample_rate_hz: int
    config: MaskConfig

    @property
    def duration_s(self) -> float:
        return len(self.audio) / float(self.sample_rate_hz)

    @property
    def peak(self) -> float:
        return float(np.max(np.abs(self.audio))) if self.audio.size else 0.0


def _raised_cosine_gate(n: int, ramp: int) -> np.ndarray:
    gate = np.ones(n, dtype=np.float64)
    ramp = min(max(int(ramp), 0), n // 2)
    if ramp:
        x = np.linspace(0, np.pi, ramp, endpoint=False)
        edge = 0.5 - 0.5 * np.cos(x)
        gate[:ramp] = edge
        gate[-ramp:] = edge[::-1]
    return gate


def _pulse_gate(config: MaskConfig, n: int) -> np.ndarray:
    fs = config.sample_rate_hz
    gate = np.zeros(n, dtype=np.float64)
    interval = max(1, round(fs / config.prf_hz))
    width = max(1, round(fs * config.matched_pulse_width_ms / 1000.0))
    ramp = round(fs * config.audio_ramp_ms / 1000.0)
    shape = _raised_cosine_gate(width, ramp)
    start0 = round(config.pre_mask_s * fs)
    end_stim = round((config.pre_mask_s + config.stimulation_duration_s) * fs)
    start = start0
    while start < min(end_stim, n):
        end = min(start + width, end_stim, n)
        gate[start:end] = shape[: end - start]
        start += interval
    return gate


def _pink_noise(rng: np.random.Generator, n: int) -> np.ndarray:
    white = rng.standard_normal(n)
    spectrum = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(n)
    scale = np.ones_like(freqs)
    nz = freqs > 0
    scale[nz] = 1.0 / np.sqrt(freqs[nz])
    scale[~nz] = 0.0
    out = np.fft.irfft(spectrum * scale, n=n)
    std = np.std(out)
    return out / std if std else out


def _narrowband_noise(rng: np.random.Generator, n: int, fs: int, center: float, bandwidth: float) -> np.ndarray:
    low = max(20.0, center - bandwidth / 2)
    high = min(fs / 2 - 100.0, center + bandwidth / 2)
    if low >= high:
        raise ValueError("Invalid narrowband center/bandwidth for this sample rate")
    noise = rng.standard_normal(n)
    sos = butter(4, [low, high], btype="bandpass", fs=fs, output="sos")
    return sosfiltfilt(sos, noise)


def _mondrian(rng: np.random.Generator, n: int, fs: int, config: MaskConfig) -> np.ndarray:
    out = np.zeros(n, dtype=np.float64)
    total_s = n / fs
    n_tones = max(1, round(total_s * config.mondrian_density_per_s))
    tone_n = max(8, round(config.mondrian_tone_ms / 1000.0 * fs))
    max_start = max(1, n - tone_n)
    for _ in range(n_tones):
        start = int(rng.integers(0, max_start))
        length = min(tone_n, n - start)
        t = np.arange(length) / fs
        freq = float(rng.uniform(300.0, min(16000.0, fs / 2 - 500.0)))
        mod = float(rng.uniform(15.0, 150.0))
        duty = float(rng.uniform(0.2, 0.8))
        phase = np.mod(t * mod, 1.0)
        pulse = (phase < duty).astype(np.float64)
        edge = _raised_cosine_gate(length, min(round(0.01 * fs), length // 2))
        out[start : start + length] += np.sin(2 * np.pi * freq * t) * pulse * edge
    peak = np.max(np.abs(out))
    return out / peak if peak else out


def _normalise(x: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(x)) if x.size else 0.0
    return x / peak if peak else x


def generate_mask(config: MaskConfig) -> GeneratedMask:
    config = config.validate()
    fs = config.sample_rate_hz
    n = round(config.total_duration_s * fs)
    t = np.arange(n, dtype=np.float64) / fs
    rng = np.random.default_rng(config.random_seed)

    gate = _pulse_gate(config, n)
    matching = np.sin(2 * np.pi * config.carrier_hz * t) * gate

    if config.profile == "simple_prf":
        background = rng.standard_normal(n)
    elif config.profile == "matched_plus_white":
        background = rng.standard_normal(n)
    elif config.profile == "matched_plus_pink":
        background = _pink_noise(rng, n)
    elif config.profile == "matched_plus_narrowband":
        background = _narrowband_noise(
            rng, n, fs, config.narrowband_center_hz, config.narrowband_bandwidth_hz
        )
    elif config.profile == "auditory_mondrian":
        background = _mondrian(rng, n, fs, config)
    else:
        raise ValueError(f"Unsupported profile: {config.profile}")

    background = _normalise(background)
    matching = _normalise(matching)

    if config.profile == "simple_prf":
        # Deliberately simple first-line profile: pulse-matched carrier plus broadband noise.
        mono = config.matching_gain * matching + config.background_gain * background
    else:
        mono = config.matching_gain * matching + config.background_gain * background

    mono = _normalise(mono) * config.master_gain
    left = mono * (1.0 - max(0.0, config.stereo_pan))
    right = mono * (1.0 + min(0.0, config.stereo_pan))
    stereo = np.column_stack([left, right]).astype(np.float32)

    if not np.all(np.isfinite(stereo)):
        raise ValueError("Generated audio contains non-finite samples")
    if np.max(np.abs(stereo), initial=0.0) > 1.0:
        raise ValueError("Generated audio exceeds digital full scale")
    if np.max(np.abs(stereo), initial=0.0) == 0.0:
        raise ValueError("Generated audio is silent")

    return GeneratedMask(stereo, fs, config)
