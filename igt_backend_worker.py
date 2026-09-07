"""Persistent command worker executed by the original Dortmund Python environment."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import traceback


RESPONSE_PREFIX = "__IGT_BRIDGE__"


def _respond(ok: bool, **fields):
    print(RESPONSE_PREFIX + json.dumps({"ok": ok, **fields}), flush=True)


def _load_adapter(path: Path):
    spec = importlib.util.spec_from_file_location("selected_dortmund_igt_adapter", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load IGT adapter: {path}")
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    for name in ("prepare", "execute", "shutdown"):
        if not callable(getattr(adapter, name, None)):
            raise TypeError(f"IGT adapter must define callable {name}()")
    return adapter


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: igt_backend_worker.py PATH_TO_IGT_ADAPTER")
    adapter_path = Path(sys.argv[1]).resolve()
    print(f"Loading Dortmund adapter: {adapter_path}", flush=True)
    adapter = _load_adapter(adapter_path)
    context = None
    closed = False

    for raw in sys.stdin:
        try:
            command = json.loads(raw)["command"]
            if command == "prepare":
                if context is not None:
                    raise RuntimeError("Dortmund backend is already prepared")
                print("Preparing through the Dortmund adapter...", flush=True)
                context = adapter.prepare()
                _respond(True, result="prepared")
            elif command == "execute":
                if context is None or closed:
                    raise RuntimeError("Dortmund backend is not prepared")
                print("Executing through the Dortmund adapter...", flush=True)
                adapter.execute(context)
                _respond(True, result="executed")
            elif command == "shutdown":
                print("Disconnecting through the Dortmund adapter...", flush=True)
                adapter.shutdown(context)
                closed = True
                _respond(True, result="disconnected")
                return 0
            else:
                raise ValueError(f"Unknown backend command: {command}")
        except BaseException as exc:
            traceback.print_exc()
            _respond(False, error=f"{type(exc).__name__}: {exc}")

    if context is not None and not closed:
        adapter.shutdown(context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
