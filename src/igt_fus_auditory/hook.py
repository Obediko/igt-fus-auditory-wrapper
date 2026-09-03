from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


class HookError(RuntimeError):
    pass


def load_hook(path: str | Path) -> ModuleType:
    """Load a site-local FUS bridge without modifying the FUS package itself."""
    path = Path(path).resolve()
    if not path.exists():
        raise HookError(f"Hook file not found: {path}")
    spec = importlib.util.spec_from_file_location("local_fus_hook", path)
    if spec is None or spec.loader is None:
        raise HookError(f"Unable to load hook: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ("prepare", "execute"):
        if not callable(getattr(module, name, None)):
            raise HookError(f"Local hook must define callable {name}()")
    return module


def validate_hook(path: str | Path) -> dict:
    module = load_hook(path)
    return {
        "path": str(Path(path).resolve()),
        "prepare": callable(getattr(module, "prepare", None)),
        "execute": callable(getattr(module, "execute", None)),
        "shutdown": callable(getattr(module, "shutdown", None)),
    }
