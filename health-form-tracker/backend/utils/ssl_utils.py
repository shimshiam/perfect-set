import os
import ssl
import sys
import threading
from contextlib import contextmanager
from typing import Iterator

import certifi


_SSL_OVERRIDE_LOCK = threading.Lock()
_DISABLE_MEDIAPIPE_SSL_WORKAROUND = "PERFECT_SET_DISABLE_MEDIAPIPE_SSL_WORKAROUND"


def _ssl_workaround_disabled() -> bool:
    value = os.getenv(_DISABLE_MEDIAPIPE_SSL_WORKAROUND, "")
    return value.lower() in {"1", "true", "yes", "on"}


def _certifi_https_context() -> ssl.SSLContext:
    """Build a verified HTTPS context using certifi's CA bundle."""
    return ssl.create_default_context(cafile=certifi.where())


@contextmanager
def mediapipe_ssl_context() -> Iterator[None]:
    """
    Scope the macOS MediaPipe certificate workaround to detector creation.

    MediaPipe may download model assets while Pose() is being initialized.
    On macOS Python installs without bundled roots, temporarily point HTTPS
    verification at certifi's CA bundle instead of mutating the process-wide
    default for the entire runtime.
    """
    if sys.platform != "darwin" or _ssl_workaround_disabled():
        yield
        return

    with _SSL_OVERRIDE_LOCK:
        original_factory = ssl._create_default_https_context
        ssl._create_default_https_context = _certifi_https_context
        try:
            yield
        finally:
            ssl._create_default_https_context = original_factory
