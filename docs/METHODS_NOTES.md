# Methods notes

## Auditory masking is independent of ultrasound ramping

`audio_ramp_ms` affects only the audible matching signal. It must never be interpreted as a command to ramp the ultrasound output.

PRESTUS currently represents pulse timing for thermal modelling but does not expose the FUS Driving System's ultrasound ramp shape/duration as equivalent protocol parameters. For that reason, ultrasound ramping should remain a separate study-level decision and should not be silently introduced by the masking wrapper.

If the ultrasound pulse changes, for example from a 20 ms rectangular pulse to a 5 ms ramp-up + 20 ms plateau + 5 ms ramp-down envelope, update the study protocol and its acoustic/thermal interpretation separately. Do not use `audio_ramp_ms` to represent that change.

## Masking strategy

The default `simple_prf` profile is intentionally conservative operationally: a reproducible pulse-matched audible carrier is combined with broadband noise. More complex profiles are available for empirical testing if the simple mask does not adequately blind participants.

The repository includes an `auditory_mondrian` option as an experimental masking profile, but complexity is not treated as intrinsically superior. Mask choice should be driven by validation with the actual transducer, headphones, stimulation timing, and active/sham discrimination.

## References / conceptual background

This implementation is informed by published and open-source work on auditory confounds in TUS, including pulse-matched masking, broadband/multitone masking, and active/sham blinding procedures. See the project README and `THIRD_PARTY_NOTICE.md` for attribution.
