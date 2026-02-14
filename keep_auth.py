import os
from uuid import getnode as get_mac

import gkeepapi


def resolve_device_id() -> str:
    """Return a stable 16-char hex Android device id for gpsoauth."""
    device_id = os.environ.get("KEEP_DEVICE_ID")
    if device_id:
        return device_id
    # gpsoauth examples typically use 16 hex chars; pad MAC-derived id for shape.
    return f"{get_mac():x}".zfill(16)


def authenticate_keep() -> gkeepapi.Keep:
    username = os.environ.get("username")
    if not username:
        raise RuntimeError("Missing required environment variable: username")

    master_key = os.environ.get("masterKey")
    if not master_key:
        raise RuntimeError("Missing required environment variable: masterKey")

    keep = gkeepapi.Keep()
    try:
        keep.authenticate(username, master_key, device_id=resolve_device_id())
    except gkeepapi.exception.LoginException as error:
        raise RuntimeError(
            "Google Keep authentication failed with current masterKey. "
            "Run './.venv/bin/python reauth_keep.py' to refresh it."
        ) from error
    return keep
