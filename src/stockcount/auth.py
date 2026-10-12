"""Who is counting? Inside LINE: a LIFF ID token checked by LINE's own server (never trust a user id
sent by the page). On the PC in dev mode: a fixed DEV_USER_ID."""
from __future__ import annotations

import httpx

LINE_VERIFY_URL = "https://api.line.me/oauth2/v2.1/verify"


class AuthError(RuntimeError):
    pass


class LineTokenVerifier:
    def __init__(self, channel_id: str, client: httpx.Client | None = None, timeout: float = 5.0):
        self.channel_id = channel_id
        self.client = client or httpx.Client(timeout=timeout)

    def verify(self, id_token: str) -> str:
        """Return the LINE user id inside a valid ID token, or raise AuthError."""
        if not id_token:
            raise AuthError("missing ID token")
        try:
            r = self.client.post(LINE_VERIFY_URL, data={"id_token": id_token, "client_id": self.channel_id})
        except httpx.HTTPError as e:
            raise AuthError("could not reach LINE to verify the token") from e
        if r.status_code != 200:
            raise AuthError(f"LINE rejected the token ({r.status_code})")
        user_id = r.json().get("sub")
        if not user_id:
            raise AuthError("the token carries no user id")
        return user_id
