"""SITE-LOCAL TEMPLATE ONLY.

Copy this file to `local_fus_hook.py` on the laboratory laptop. That file is
.gitignored and should be completed together with the local FUS maintainer.

Do NOT copy transducer IDs, generator IDs, calibration data, conversion data,
pressure settings, steering tables, or sequence definitions into this repository.
The hook should only call the already-approved local FUS study code.
"""


def prepare():
    """Prepare the already-configured local FUS backend and return its context.

    Replace the placeholder import below with the lab-approved local entry point.
    Preparation should establish whatever existing connection/sequence state is
    needed before the auditory mask starts. It should not duplicate configuration.
    """
    raise RuntimeError(
        "Site integration is intentionally not configured. Complete local_fus_hook.py "
        "with Christoph/Margely-approved local FUS code before active use."
    )


def execute(context):
    """Execute the sequence that was prepared by the existing FUS installation."""
    raise RuntimeError("Site integration is intentionally not configured")


def shutdown(context):
    """Optional cleanup for the existing local FUS backend."""
    return None
