from __future__ import annotations

import importlib
import time
import numpy as np


class AudioError(RuntimeError):
    pass


class AudioPlayer:
    def __init__(self, output_device=None):
        self.output_device = output_device
        try:
            self.sd = importlib.import_module("sounddevice")
        except ImportError as exc:
            raise AudioError("sounddevice is required for verified stereo playback") from exc

    def list_devices(self):
        return self.sd.query_devices()

    def verify(self, sample_rate_hz: int) -> dict:
        try:
            device = self.sd.query_devices(self.output_device, "output")
            if int(device.get("max_output_channels", 0)) < 2:
                raise AudioError("Selected output does not provide stereo playback")
            self.sd.check_output_settings(
                device=self.output_device,
                channels=2,
                samplerate=sample_rate_hz,
                dtype="float32",
            )
            return dict(device)
        except AudioError:
            raise
        except Exception as exc:
            raise AudioError("Unable to verify the selected audio output") from exc

    def play(self, audio: np.ndarray, sample_rate_hz: int) -> dict:
        requested = time.perf_counter()
        try:
            self.sd.play(
                np.asarray(audio, dtype=np.float32),
                samplerate=sample_rate_hz,
                device=self.output_device,
                blocking=False,
            )
            stream = self.sd.get_stream()
            if not getattr(stream, "active", False):
                raise AudioError("Audio stream did not become active")
            latency = getattr(stream, "latency", 0.0)
            if hasattr(latency, "output"):
                latency = latency.output
            latency_s = max(0.0, float(latency or 0.0))
            return {
                "requested_at_monotonic": requested,
                "stream_active_at_monotonic": time.perf_counter(),
                "estimated_latency_s": latency_s,
            }
        except AudioError:
            raise
        except Exception as exc:
            raise AudioError("Audio playback failed") from exc

    def wait(self):
        try:
            self.sd.wait()
        except Exception as exc:
            raise AudioError("Audio playback stopped unexpectedly") from exc

    def stop(self):
        try:
            self.sd.stop()
        except Exception:
            pass
