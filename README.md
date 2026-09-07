# IGT FUS Auditory Masking Wrapper

A small, hardware-agnostic auditory masking layer designed to sit **around** an already-configured FUS Driving System without replacing or editing its device, transducer, generator, calibration, conversion, steering, pressure, or ultrasound-waveform configuration.

The intended deployment is a separate folder such as:

```text
Desktop\Obed\igt-fus-auditory-wrapper
```

The FUS Driving System remains the backend and single source of truth for ultrasound delivery.

## Why this repository exists

The earlier combined repository bundled a full FUS package together with auditory masking. That is useful as a software snapshot, but it is not the cleanest way to add masking to a lab laptop whose FUS installation has already been configured and validated by the local team.

This repository separates the two responsibilities:

```text
Auditory wrapper                     Existing FUS installation
----------------                     -------------------------
Generate/freeze mask                 Current device names
Select/check headphones              Current transducer/generator files
Play same WAV active/sham    --->    Current calibration/conversion files
Log mask timing                      Current sequence validation
Call local approved hook             Actual ultrasound execution
```

The arrow is a **thin local hook**, not a copied FUS configuration.

## Safety and configuration boundary

This repository intentionally contains **none** of the following:

- IGT device IDs
- transducer IDs
- generator configuration
- calibration or conversion JSON
- equalization/focus/power curves
- FUS `.ini` files
- proprietary device libraries
- ultrasound pressure/amplitude settings
- steering/focus settings
- ultrasound pulse-ramp settings

The wrapper cannot infer or replace those values.

## Masking profiles

The software provides:

- `simple_prf` - recommended starting point: pulse-matched audible carrier + broadband noise
- `matched_plus_white`
- `matched_plus_pink`
- `matched_plus_narrowband`
- `auditory_mondrian` - optional experimental multitone/random mask

The more complex options are available, not mandatory. Start simple, test active-versus-sham perceptibility on the actual setup, and only add complexity if it improves blinding.

## Important distinction: audio ramp vs ultrasound ramp

`audio_ramp_ms` smooths only the **headphone masking waveform**. It does not change the ultrasound pulse.

Ultrasound ramping remains entirely under the local FUS Driving System and study protocol. This separation is especially important because PRESTUS does not currently expose the FUS Driving System's ultrasound ramp shape/duration as equivalent protocol parameters. The masking wrapper therefore never silently introduces an ultrasound ramp.

## First setup on the lab laptop

See [`docs/SETUP_AT_LAB.md`](docs/SETUP_AT_LAB.md).

In short:

```bat
cd Desktop\Obed\igt-fus-auditory-wrapper
scripts\setup_windows.bat
.venv\Scripts\python -m igt_fus_auditory devices
copy config\study_mask.example.json config\study_mask.local.json
.venv\Scripts\python -m igt_fus_auditory audio-test --config config\study_mask.local.json --seconds 3
```

After the headphone output is measured/approved, freeze the final WAV:

```bat
.venv\Scripts\python -m igt_fus_auditory generate ^
  --config config\study_mask.local.json ^
  --out masks\study_mask.wav
```

The WAV is stored with a JSON sidecar containing the configuration and a SHA-256 hash.

## Operator GUI

The Windows operator interface stays in the isolated wrapper folder and does not copy or edit the laboratory FUS installation.

After setup, launch it by double-clicking:

```text
start_auditory_wrapper.bat
```

The interface provides speaker selection, a three-second audio test, deterministic mask generation and verification, sham operation, guarded active operation, live status, and session logs. It also provides a Browse field for selecting the laptop-local IGT adapter. That selected path is stored only in `config/gui.local.json`, which is excluded from Git.

For the GUI-selectable Dortmund bridge, copy:

```text
examples\dortmund_gui_hook.example.py
```

to:

```text
local_fus_hook.py
```

The GUI passes the selected adapter path to that hook at runtime. Device identities, pressure, focus, timing, calibration and conversion data remain in the selected local adapter and are not stored in this repository.

The GUI does not present a software button as a reliable FUS emergency stop. Once active delivery has been dispatched, use the laboratory hardware emergency-stop procedure if interruption is required.

## Connecting to the FUS Driving System

Copy:

```text
examples\local_fus_hook.example.py
```

to:

```text
local_fus_hook.py
```

That local file is excluded from Git. Complete it on the TUS laptop with the local FUS maintainer so it calls the **current, already-approved FUS study code**.

The wrapper expects only:

```python
def prepare():
    return context


def execute(context):
    ...
```

The wrapper calls `prepare()` before mask onset, waits through the pre-mask interval, then calls `execute(context)`. It does not create the generator/transducer configuration itself.

See [`docs/WRAPPER_INTEGRATION.md`](docs/WRAPPER_INTEGRATION.md).

## Active and sham

Sham runs the same frozen auditory mask without calling the FUS hook.

Active execution is explicitly locked unless `--confirm-active` is supplied locally:

```bat
python -m igt_fus_auditory active ^
  --mask masks\study_mask.wav ^
  --hook local_fus_hook.py ^
  --confirm-active
```

This flag is not a substitute for local safety approval; it only prevents accidental software execution.

## Validation order

Use [`docs/VALIDATION_CHECKLIST.md`](docs/VALIDATION_CHECKLIST.md). The intended order is:

1. audio generation
2. output-device check
3. headphone-level validation
4. mock wrapper timing
5. local-hook review
6. non-participant FUS validation
7. active/sham perceptibility validation

## Installation

Python 3.9+:

```bash
python -m pip install -e .
```

Dependencies are limited to NumPy, SciPy and SoundDevice.

## Attribution

The implementation is conceptually informed by the work of Hira Musarrat & Benjamin Kop, Marwan Engels, and the TUS auditory-confound/masking literature. No NeuroFUS/TPO control code or device-specific FUS package is vendored here. See [`THIRD_PARTY_NOTICE.md`](THIRD_PARTY_NOTICE.md).

## Status

Version `0.1.0` is a deployment-ready **wrapper scaffold**. The one intentionally site-specific piece is `local_fus_hook.py`, because current equipment names and the approved sequence should come from the lab's installed FUS system rather than from this repository.
