from pathlib import Path


def test_no_device_artifacts_bundled():
    root = Path(__file__).resolve().parents[1]
    forbidden_suffixes = {".ini", ".pyd", ".dll"}
    forbidden_name_fragments = (
        "equalizationcurve",
        "focuscurvefit",
        "powercurvefit",
        "voltagecurvefit",
        "conversion_data",
    )
    offenders = []
    for p in root.rglob("*"):
        if not p.is_file() or ".venv" in p.parts or ".git" in p.parts:
            continue
        lower = p.name.lower()
        if p.suffix.lower() in forbidden_suffixes or any(x in lower for x in forbidden_name_fragments):
            offenders.append(str(p.relative_to(root)))
    assert offenders == []
