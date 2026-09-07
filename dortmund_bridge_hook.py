"""Bridge the isolated auditory wrapper to Dortmund's native FUS environment."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent
WORKER = ROOT / "igt_backend_worker.py"
DEFAULT_DORTMUND_PYTHON = Path(
    r"C:\Users\TUS\FUS-driving-software\venv\FUS_DS_PACKAGE\Scripts\python.exe"
)
DEFAULT_DORTMUND_ROOT = Path(r"C:\Users\TUS\FUS-driving-software")
RESPONSE_PREFIX = "__IGT_BRIDGE__"


def _require_file(raw: str, label: str) -> Path:
    path = Path(raw).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"{label} not found: {path}")
    return path


def _command(process: subprocess.Popen, command: str):
    if process.poll() is not None:
        raise RuntimeError(f"Dortmund backend exited with status {process.returncode}")
    process.stdin.write(json.dumps({"command": command}) + "\n")
    process.stdin.flush()
    for line in process.stdout:
        if line.startswith(RESPONSE_PREFIX):
            response = json.loads(line[len(RESPONSE_PREFIX):])
            if response.get("ok"):
                return response.get("result")
            raise RuntimeError(response.get("error", "Dortmund backend command failed"))
        print(line, end="", flush=True)
    raise RuntimeError(f"Dortmund backend stopped during {command} with status {process.wait()}")


def prepare():
    adapter = _require_file(os.environ.get("IGT_FUS_ADAPTER_PATH", ""), "IGT adapter")
    python_path = _require_file(
        os.environ.get("IGT_FUS_PYTHON", str(DEFAULT_DORTMUND_PYTHON)),
        "Dortmund Python",
    )
    worker = _require_file(str(WORKER), "IGT backend worker")
    dortmund_root = Path(os.environ.get("IGT_FUS_ROOT", str(DEFAULT_DORTMUND_ROOT))).resolve()
    if not dortmund_root.is_dir():
        raise FileNotFoundError(f"Dortmund FUS root not found: {dortmund_root}")

    environment = os.environ.copy()
    environment["PYTHONUNBUFFERED"] = "1"
    print(f"Starting Dortmund backend with: {python_path}", flush=True)
    process = subprocess.Popen(
        [str(python_path), "-u", str(worker), str(adapter)],
        cwd=str(dortmund_root),
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    context = {"process": process, "closed": False}
    try:
        _command(process, "prepare")
        return context
    except BaseException:
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=5)
        raise


def execute(context):
    if context.get("closed"):
        raise RuntimeError("Cannot execute: Dortmund backend is closed")
    return _command(context["process"], "execute")


def shutdown(context):
    if context is None or context.get("closed"):
        return None
    process = context["process"]
    try:
        if process.poll() is None:
            _command(process, "shutdown")
            process.wait(timeout=5)
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        context["closed"] = True
