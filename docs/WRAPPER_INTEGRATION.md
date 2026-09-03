# Wrapper integration with the existing FUS Driving System

## Design rule

The installed FUS Driving System remains the single source of truth for:

- driving-system identity
- transducer identity
- generator configuration
- calibration and conversion files
- pressure/amplitude conversion
- steering/focus configuration
- ultrasound pulse shape and ramping
- sequence validation and device connection

The auditory wrapper owns only:

- auditory waveform generation
- headphone selection/checking
- frozen WAV + hash metadata
- mask timing around the stimulation window
- active/sham auditory consistency
- wrapper event logging

## Why the hook is local

Equipment names and local FUS configuration can change when the Donders/Radboud software is updated. Hard-coding those values into a public auditory repository would create configuration drift and could lead to the wrapper using stale device names.

The integration therefore uses a small untracked file, `local_fus_hook.py`, that adapts the wrapper to the *current* lab installation.

The wrapper expects only:

```python
def prepare():
    ...
    return context


def execute(context):
    ...
```

An optional `shutdown(context)` may also be defined.

`prepare()` is called **before** masking starts. This allows the existing FUS backend to connect and prepare its approved sequence without consuming the pre-mask interval.

`execute(context)` is called after the configured pre-mask interval. It should do only what the approved local study runner normally does to execute the already-prepared sequence.

## Important: do not recreate the FUS sequence here

Do not duplicate the local FUS main script, transducer names, generator names, calibration/conversion paths, pressure settings, or ramp settings inside `local_fus_hook.py` if those are already defined by the existing installation.

The preferred integration is to import/call the existing local study entry point.

## Validation order

1. Audio-only test with no FUS import.
2. Mock hook test using `examples/mock_fus_hook.py`.
3. Import-only validation of the local hook:

```bat
.venv\Scripts\python -m igt_fus_auditory validate-hook --hook local_fus_hook.py
```

This imports the file but does not call `prepare()` or `execute()`.

4. Team-reviewed integration with the local FUS environment.
5. Water-tank / non-participant validation according to the lab workflow.
6. Active/sham perceptibility validation with the approved setup.

## Python-environment note

The isolated `.venv` is recommended for generating/testing audio. For active integration, if the local FUS package is only importable from its own Python environment, use the FUS environment's Python to run the wrapper source or agree with the local maintainer on the cleanest import bridge. This does **not** require editing the FUS package files, but any environment change should be agreed locally.

Do not install or overwrite FUS calibration/configuration files as part of auditory setup.
