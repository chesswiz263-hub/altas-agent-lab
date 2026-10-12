"""Single-operator hosted browser login. Not a multi-user identity platform.

All dashboard/API/docs paths are gated by a short-lived signed, HttpOnly cookie.
Unsafe API methods require a derived CSRF token and same-origin checks.
"""
from __future__ import annotations

import base64
from collections import defaultdict, deque
from dataclasses import dataclass, field
import hashlib
import hmac
import os
import secrets
import time
from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

SESSION_COOKIE = "atlas_session"
SESSION_SECONDS = 8 * 60 * 60
LOGIN_WINDOW_SECONDS = 5 * 60
LOGIN_MAX_ATTEMPTS = 10


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "yes", "true", "on"}


@dataclass
class WebAuth:
    enabled: bool
    password: str = ""
    secret: bytes = b""
    secure: bool = True
    public_origin: str = ""
    # One ASGI worker; limiter is deliberately process-local, not distributed.
    attempts: dict[str, deque] = field(default_factory=lambda: defaultdict(deque))

    @classmethod
    def from_environment(cls) -> "WebAuth":
        enabled = _truthy("ATLAS_HOSTED_MODE")
        if not enabled:
            return cls(False)
        password = os.environ.get("ATLAS_ADMIN_PASSWORD", "")
        secret = os.environ.get("ATLAS_SESSION_SECRET", "")
        origin = os.environ.get("ATLAS_PUBLIC_ORIGIN", "").strip().rstrip("/")
        if not origin and os.getenv("RENDER_EXTERNAL_HOSTNAME"):
            origin = "https://" + os.environ["RENDER_EXTERNAL_HOSTNAME"].strip().lower()
        if len(password) < 16 or len(secret) < 32 or password == secret:
            raise RuntimeError("Hosted mode requires different ATLAS_ADMIN_PASSWORD (16+ chars) "
                               "and ATLAS_SESSION_SECRET (32+ chars)")
        if origin:
            parsed = urlsplit(origin)
            if parsed.scheme != "https" or not parsed.hostname or parsed.path not in {"", "/"} or parsed.query or parsed.fragment or parsed.username:
                raise RuntimeError("ATLAS_PUBLIC_ORIGIN must be an HTTPS origin without a path or credentials")
        return cls(True, password, secret.encode(), True, origin)

    def _sign(self, value: str) -> str:
        return hmac.new(self.secret, value.encode(), hashlib.sha256).hexdigest()

    def session(self) -> str:
        payload = f"{int(time.time())}:{secrets.token_urlsafe(24)}"
        encoded = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
        return encoded + "." + self._sign(encoded)

    def valid_session(self, candidate: str) -> bool:
        if not candidate or len(candidate) > 512 or "." not in candidate:
            return False
        value, digest = candidate.rsplit(".", 1)
        if not hmac.compare_digest(self._sign(value), digest):
            return False
        try:
            payload = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode()
            timestamp, nonce = payload.split(":", 1)
            age = time.time() - int(timestamp)
            return 0 <= age <= SESSION_SECONDS and 24 <= len(nonce) <= 80
        except (ValueError, UnicodeError):
            return False

    def csrf(self, session: str) -> str:
        return self._sign("csrf:" + session)

    def verify_csrf(self, request: Request, session: str) -> bool:
        return hmac.compare_digest(request.headers.get("X-Atlas-CSRF", ""), self.csrf(session))

    def same_origin(self, request: Request) -> bool:
        fetch_site = request.headers.get("sec-fetch-site", "")
        if fetch_site and fetch_site not in {"same-origin", "none"}:
            return False
        origin = request.headers.get("origin")
        if not origin:
            # CSRF token is still compulsory on authenticated mutations.
            return True
        if self.public_origin:
            return hmac.compare_digest(origin, self.public_origin)
        # For Codespaces and other private previews, compare to actual request host.
        candidate = f"{request.url.scheme}://{request.headers.get('host', '')}"
        return hmac.compare_digest(origin, candidate)

    def verify_password(self, password: str) -> bool:
        # Digest both sides to avoid length-sensitive raw string comparison.
        supplied = hashlib.sha256(password.encode()).digest()
        expected = hashlib.sha256(self.password.encode()).digest()
        return hmac.compare_digest(supplied, expected)

    def login_allowed(self, client_key: str) -> bool:
        now = time.monotonic()
        entries = self.attempts[client_key]
        while entries and entries[0] <= now - LOGIN_WINDOW_SECONDS:
            entries.popleft()
        if len(entries) >= LOGIN_MAX_ATTEMPTS:
            return False
        entries.append(now)  # count successful attempts too
        return True

    def login_success(self, client_key: str) -> None:
        self.attempts.pop(client_key, None)

    def reject(self, request: Request) -> Response:
        if request.url.path.startswith("/api/") or request.url.path.startswith("/auth/"):
            return JSONResponse({"detail": "Please sign in to ATLAS"}, status_code=401,
                                headers={"Cache-Control": "no-store"})
        return RedirectResponse(url="/login", status_code=303)

    def set_cookie(self, response: Response, session: str) -> None:
        response.set_cookie(SESSION_COOKIE, session, max_age=SESSION_SECONDS, httponly=True,
                            secure=self.secure, samesite="strict", path="/")
