from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from .config import MaskConfig
from .signals import GeneratedMask


def _pcm16(audio: np.ndarray) -> np.ndarray:
    return np.rint(np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)


def save_mask(generated: GeneratedMask, wav_path: str | Path) -> tuple[Path, Path]:
    wav_path = Path(wav_path).with_suffix(".wav")
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    pcm = _pcm16(generated.audio)
    wavfile.write(str(wav_path), generated.sample_rate_hz, pcm)
    digest = hashlib.sha256(np.ascontiguousarray(pcm).tobytes()).hexdigest()
    metadata = {
        "format_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "audio_sha256": digest,
        "sample_rate_hz": generated.sample_rate_hz,
        "duration_s": generated.duration_s,
        "channels": 2,
        "expected_pulses": generated.config.expected_pulses,
        "config": generated.config.to_dict(),
        "boundary_notice": (
            "This file describes auditory masking only. It does not configure or verify "
            "ultrasound hardware, calibration, conversion data, pressure, steering, or sonication ramps."
        ),
    }
    sidecar = wav_path.with_suffix(".json")
    sidecar.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return wav_path, sidecar


def load_mask(wav_path: str | Path) -> GeneratedMask:
    wav_path = Path(wav_path)
    sidecar = json.loads(wav_path.with_suffix(".json").read_text(encoding="utf-8"))
    fs, pcm = wavfile.read(str(wav_path))
    if pcm.dtype != np.int16:
        raise ValueError("Frozen masks must be 16-bit PCM WAV files")
    digest = hashlib.sha256(np.ascontiguousarray(pcm).tobytes()).hexdigest()
    if digest != sidecar.get("audio_sha256"):
        raise ValueError("WAV hash does not match its sidecar metadata")
    if int(fs) != int(sidecar.get("sample_rate_hz", -1)):
        raise ValueError("WAV sample rate does not match its sidecar metadata")
    config = MaskConfig(**sidecar["config"]).validate()
    audio = pcm.astype(np.float32) / 32767.0
    return GeneratedMask(audio=audio, sample_rate_hz=int(fs), config=config)
