# Validation checklist

## Repository boundary

- [ ] Wrapper is located under `Desktop\Obed`.
- [ ] No wrapper file has been copied into FUS configuration folders.
- [ ] No transducer/generator/calibration/conversion files are stored in this repository.
- [ ] `local_fus_hook.py` is present locally but remains untracked.

## Auditory waveform

- [ ] Final masking profile is agreed (`simple_prf` first unless there is a reason to use a more complex option).
- [ ] Audible matching PRF matches the intended study timing.
- [ ] Audible matching pulse width is documented.
- [ ] Audio ramp is clearly identified as an **auditory** ramp, not an ultrasound ramp.
- [ ] Frozen WAV hash matches its JSON sidecar.
- [ ] Same frozen WAV is used for active and sham.

## Headphones

- [ ] Correct physical output device selected.
- [ ] Stereo playback verified.
- [ ] Actual output level measured/approved using the lab procedure.
- [ ] Output does not clip digitally.
- [ ] Headphone placement is standardized.

## FUS integration

- [ ] Current FUS installation is working independently before wrapper integration.
- [ ] Current equipment names are obtained from the local installation, not this repository.
- [ ] Existing calibration/conversion files remain unchanged.
- [ ] `local_fus_hook.py` calls the approved local study code rather than recreating hardware setup.
- [ ] `prepare()` completes before auditory playback begins.
- [ ] `execute()` produces the expected sequence in the non-participant validation setup.
- [ ] Any FUS console errors are resolved with the FUS maintainers before participant use.

## Blinding

- [ ] Active and sham receive the same auditory WAV and timing structure.
- [ ] Participants cannot reliably distinguish active from sham in validation, or any residual discrimination is documented.
- [ ] If simple masking is sufficient, keep it; only move to more complex masking if validation shows a need.
