from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import time

from .audio import AudioPlayer
from .hook import load_hook
from .signals import GeneratedMask


class SessionError(RuntimeError):
    pass


def _log(log_path: Path | None, event: str, **details):
    row = {
        "event": event,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "monotonic_s": time.perf_counter(),
        **details,
    }
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def run_sham(mask: GeneratedMask, log_path: str | Path | None = None):
    config = mask.config.validate()
    if not config.headphones_calibrated:
        raise SessionError("Headphones are not marked calibrated in the mask config")
    log_path = Path(log_path) if log_path else None
    player = AudioPlayer(config.output_device)
    player.verify(mask.sample_rate_hz)
    _log(log_path, "audio_verified", condition="masked")
    player.play(mask.audio, mask.sample_rate_hz)
    _log(log_path, "mask_started", condition="masked")
    time.sleep(config.pre_mask_s)
    _log(log_path, "stimulation_window_started", condition="masked")
    time.sleep(config.stimulation_duration_s)
    _log(log_path, "stimulation_window_complete", condition="masked")
    player.wait()
    _log(log_path, "session_complete", condition="masked")


def run_active(
    mask: GeneratedMask,
    hook_path: str | Path,
    *,
    allow_active: bool = False,
    log_path: str | Path | None = None,
):
    """Wrap an already-approved local FUS sequence with auditory playback.

    The wrapper never creates equipment objects, chooses hardware IDs, loads
    calibration/conversion files, defines ultrasound pressure, or changes the
    sonication waveform. Those responsibilities remain entirely in the site-local
    FUS installation and hook.
    """
    if not allow_active:
        raise SessionError("Active execution is locked; explicit local confirmation is required")
    config = mask.config.validate()
    if not config.headphones_calibrated:
        raise SessionError("Headphones are not marked calibrated in the mask config")

    log_path = Path(log_path) if log_path else None
    hook = load_hook(hook_path)
    player = AudioPlayer(config.output_device)
    player.verify(mask.sample_rate_hz)
    _log(log_path, "audio_verified", condition="masked")

    context = None
    started = False
    try:
        # Prepare the existing FUS backend before auditory onset so connection/setup
        # latency does not consume the intended pre-mask interval.
        context = hook.prepare()
        _log(log_path, "fus_backend_prepared", condition="masked")

        player.play(mask.audio, mask.sample_rate_hz)
        started = True
        _log(log_path, "mask_started", condition="masked")
        time.sleep(config.pre_mask_s)

        _log(log_path, "stimulation_dispatch", condition="masked")
        hook.execute(context)
        _log(log_path, "stimulation_returned", condition="masked")

        player.wait()
        _log(log_path, "session_complete", condition="masked")
    except BaseException as exc:
        _log(log_path, "session_aborted", condition="masked", error_type=type(exc).__name__)
        if started:
            player.stop()
        raise
    finally:
        shutdown = getattr(hook, "shutdown", None)
        if callable(shutdown):
            shutdown(context)
