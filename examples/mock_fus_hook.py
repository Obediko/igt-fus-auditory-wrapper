"""No-hardware mock hook used only to test wrapper timing."""

import time


def prepare():
    return {"prepared": True}


def execute(context):
    assert context["prepared"]
    time.sleep(0.05)


def shutdown(context):
    return None
