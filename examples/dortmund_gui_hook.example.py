"""GUI-compatible laptop-local bridge to a selected IGT adapter.

Copy this file to ``local_fus_hook.py`` in the wrapper root. The GUI supplies
the selected adapter path through ``IGT_FUS_ADAPTER_PATH``. Device identities,
calibration, conversion data and ultrasound parameters remain in that local
adapter and are never copied into this repository.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys


FUS_PACKAGE_ROOT = Path(r"C:\Users\TUS\FUS-driving-software\fus_ds_package")


def _load_adapter():
    raw_path = os.environ.get("IGT_FUS_ADAPTER_PATH", "").strip()
    if not raw_path:
        raise RuntimeError("No IGT adapter path was selected in the auditory-wrapper GUI")

    adapter_path = Path(raw_path).expanduser().resolve()
    if not adapter_path.is_file():
        raise FileNotFoundError(f"IGT adapter not found: {adapter_path}")
    if not FUS_PACKAGE_ROOT.is_dir():
        raise FileNotFoundError(f"Dortmund FUS package not found: {FUS_PACKAGE_ROOT}")

    package_root = str(FUS_PACKAGE_ROOT)
    if package_root not in sys.path:
        sys.path.insert(0, package_root)

    spec = importlib.util.spec_from_file_location("selected_local_igt_adapter", adapter_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load IGT adapter: {adapter_path}")
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)

    for name in ("prepare", "execute", "shutdown"):
        if not callable(getattr(adapter, name, None)):
            raise TypeError(f"Selected IGT adapter must define callable {name}()")
    return adapter


def prepare():
    adapter = _load_adapter()
    delivery_context = adapter.prepare()
    return {"adapter": adapter, "delivery_context": delivery_context}


def execute(context):
    return context["adapter"].execute(context["delivery_context"])


def shutdown(context):
    if context is None:
        return None
    return context["adapter"].shutdown(context["delivery_context"])
