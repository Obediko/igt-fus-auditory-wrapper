# Setup on the TUS laptop

This repository is intended to live entirely under `Desktop\Obed`. It does **not** replace or modify the installed FUS Driving System.

## 1. Copy only this repository

Recommended location:

```text
C:\Users\<user>\Desktop\Obed\igt-fus-auditory-wrapper\
```

Do not copy files from this repository into the FUS Driving System `config`, `igt`, transducer, generator, calibration, or conversion folders.

## 2. Create an isolated auditory environment

From PowerShell or Command Prompt in the repository folder:

```bat
scripts\setup_windows.bat
```

This creates `.venv` inside the wrapper folder and installs only the auditory-wrapper dependencies.

## 3. Select the headphones

Activate the environment and list devices:

```bat
.venv\Scripts\python -m igt_fus_auditory devices
```

Record the intended output device in a local copy of `config\study_mask.example.json`.

## 4. Run the audio-only check

```bat
.venv\Scripts\python -m igt_fus_auditory audio-test --config config\study_mask.local.json --seconds 3
```

This command cannot connect to the FUS system.

## 5. Calibrate/approve headphone level

Digital gain is not SPL. Measure the actual headphone output using the lab-approved procedure. Only after this validation should `headphones_calibrated` be set to `true` in the local study mask config.

## 6. Generate and freeze the study WAV

```bat
.venv\Scripts\python -m igt_fus_auditory generate --config config\study_mask.local.json --out masks\study_mask.wav
```

The wrapper creates:

- `study_mask.wav`
- `study_mask.json` containing the configuration and SHA-256 hash

Use the same frozen WAV for active and sham sessions unless the study protocol explicitly requires otherwise.

## 7. Create the site-local FUS hook

Copy:

```text
examples\local_fus_hook.example.py
```

to:

```text
local_fus_hook.py
```

`local_fus_hook.py` is excluded from Git. Complete it together with the local FUS maintainer so it calls the **already-configured** FUS study code. No equipment/calibration data should be copied into this repository.

See `WRAPPER_INTEGRATION.md` before active testing.
