from __future__ import annotations

import os
from typing import Any, Optional


def _get_client_hostname(client: Any) -> Optional[str]:
    for attr in ("hostname", "host", "_hostname", "_host", "api_host"):
        v = getattr(client, attr, None)
        if isinstance(v, str) and v.strip():
            return v.strip().lower()
    cfg = getattr(client, "config", None)
    if cfg is not None:
        for attr in ("hostname", "host", "_hostname", "_host"):
            v = getattr(cfg, attr, None)
            if isinstance(v, str) and v.strip():
                return v.strip().lower()
    return None


def _guards_disabled() -> bool:
    v = (os.getenv("AMADEUS_DISABLE_PROD_BOOKING") or "1").strip().lower()
    return v in {"0", "false", "no"}


def ensure_booking_is_sandbox(client: Any) -> None:
    """Layer-2 runtime guard: refuse booking unless the client is definitely sandbox."""
    if _guards_disabled():
        return
    hn = _get_client_hostname(client)
    if hn is None:
        raise RuntimeError(
            "Booking safety check: cannot determine Amadeus client hostname. Refusing to book."
        )
    if hn not in {"test", "sandbox"}:
        raise RuntimeError(
            f"Booking safety check: booking client hostname='{hn}' is not sandbox/test. Refusing to book."
        )
