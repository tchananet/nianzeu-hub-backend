"""One httpx client per virtual user, carrying its synthetic source address.

The source header only reaches the quota keys when the target sits behind the
authorised test proxy and uvicorn trusts it (``FORWARDED_ALLOW_IPS``, GAP-02).
``tests/load/attribution.py`` proves that before a run; without the proof the
whole run collapses onto one IP and measures nothing but rate limiting.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx

from tests.load.config import LoadConfig
from tests.load.corpus import Account
from tests.load.metrics import Recorder


class LoginRefused(RuntimeError):
    """Login did not yield a session; the caller must abort rather than guess."""


@dataclass
class UserSession:
    config: LoadConfig
    account: Account
    recorder: Recorder
    started: float
    client: httpx.Client = field(init=False)
    csrf: str | None = field(default=None, init=False)
    last: httpx.Response | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.client = httpx.Client(
            base_url=self.config.base_url,
            timeout=self.config.timeout_s,
            headers={self.config.source_header: self.account.source},
            follow_redirects=False,
        )

    def close(self) -> None:
        self.client.close()

    def _minute(self) -> int:
        return int((time.monotonic() - self.started) // 60)

    def call(self, journey: str, method: str, path: str, **kwargs: object) -> int:
        """Issue one request, record its latency and status, and return the status."""
        begin = time.perf_counter()
        try:
            response = self.client.request(method, path, **kwargs)  # type: ignore[arg-type]
        except httpx.TimeoutException:
            self.recorder.fail(journey, "timeout", self._minute())
            return 0
        except httpx.HTTPError as error:
            self.recorder.fail(journey, type(error).__name__, self._minute())
            return 0
        elapsed_ms = (time.perf_counter() - begin) * 1000
        self.recorder.record(journey, response.status_code, elapsed_ms, self._minute())
        self.last = response
        return response.status_code

    def login(self) -> None:
        """Log in once at the start of the run, per the A01 scenario."""
        status = self.call("login", "POST", "/api/v1/auth/login", json={
            "email": self.account.email, "password": self.account.password,
        }, headers={
            "Origin": self.config.origin,
            "X-Auth-Intent": "session",
            "Content-Type": "application/json",
        })
        if status != 200:
            raise LoginRefused(f"login returned {status} for {self.account.email}")
        self.refresh_csrf()

    def refresh_csrf(self) -> None:
        status = self.call("csrf", "GET", "/api/v1/auth/csrf",
                           headers={"Origin": self.config.origin})
        body = self.last.json() if status == 200 and self.last is not None else {}
        self.csrf = body.get("csrf_token")

    def mutation_headers(self) -> dict[str, str]:
        if self.csrf is None:
            self.refresh_csrf()
        return {
            "Origin": self.config.origin,
            "Content-Type": "application/json",
            "X-CSRF-Token": self.csrf or "",
        }
