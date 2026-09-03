from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path

from .audio import AudioPlayer
from .config import MaskConfig
from .hook import validate_hook
from .maskfile import load_mask, save_mask
from .session import run_active, run_sham
from .signals import generate_mask


def _config(path: str) -> MaskConfig:
    return MaskConfig.from_json(path)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="igt-auditory")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("generate", help="Generate a deterministic mask and JSON sidecar")
    p.add_argument("--config", required=True)
    p.add_argument("--out", required=True)

    sub.add_parser("devices", help="List available audio devices")

    p = sub.add_parser("audio-test", help="Play a short audio-only test; never touches FUS")
    p.add_argument("--config", required=True)
    p.add_argument("--seconds", type=float, default=3.0)

    p = sub.add_parser("validate-hook", help="Import and inspect a local FUS hook without calling prepare/execute")
    p.add_argument("--hook", required=True)

    p = sub.add_parser("sham", help="Run the masking/sham timing only")
    p.add_argument("--mask", required=True)
    p.add_argument("--log", default="logs/session.jsonl")

    p = sub.add_parser("active", help="Wrap an existing locally approved FUS hook")
    p.add_argument("--mask", required=True)
    p.add_argument("--hook", required=True)
    p.add_argument("--log", default="logs/session.jsonl")
    p.add_argument("--confirm-active", action="store_true")

    args = parser.parse_args(argv)

    if args.cmd == "generate":
        generated = generate_mask(_config(args.config))
        wav, meta = save_mask(generated, args.out)
        print(wav)
        print(meta)
    elif args.cmd == "devices":
        print(AudioPlayer().list_devices())
    elif args.cmd == "audio-test":
        cfg = _config(args.config)
        test_cfg = replace(
            cfg,
            stimulation_duration_s=max(0.5, float(args.seconds)),
            pre_mask_s=0.0,
            post_mask_s=0.0,
            headphones_calibrated=True,
        )
        generated = generate_mask(test_cfg)
        player = AudioPlayer(test_cfg.output_device)
        print(json.dumps(player.verify(test_cfg.sample_rate_hz), indent=2, default=str))
        player.play(generated.audio, generated.sample_rate_hz)
        player.wait()
    elif args.cmd == "validate-hook":
        print(json.dumps(validate_hook(args.hook), indent=2))
    elif args.cmd == "sham":
        run_sham(load_mask(args.mask), args.log)
    elif args.cmd == "active":
        run_active(
            load_mask(args.mask),
            args.hook,
            allow_active=args.confirm_active,
            log_path=args.log,
        )


if __name__ == "__main__":
    main()
