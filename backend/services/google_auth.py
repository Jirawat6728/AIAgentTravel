from __future__ import annotations

import os
from typing import Any, Dict

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

GOOGLE_CLIENT_ID = (os.getenv("GOOGLE_CLIENT_ID") or "").strip()


def verify_google_id_token(token: str) -> Dict[str, Any]:
    """Verify Google ID token (from Google Identity Services).

    Returns the decoded claims if valid, otherwise raises ValueError.
    """
    if not GOOGLE_CLIENT_ID:
        raise ValueError("GOOGLE_CLIENT_ID not set on backend")

    req = google_requests.Request()
    claims = google_id_token.verify_oauth2_token(token, req, GOOGLE_CLIENT_ID)

    # Basic sanity
    if claims.get("aud") != GOOGLE_CLIENT_ID:
        raise ValueError("Invalid token audience")
    if not claims.get("sub") or not claims.get("email"):
        raise ValueError("Missing required claims")
    return claims
