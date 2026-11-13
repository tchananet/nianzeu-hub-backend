"""Run configuration, read from the environment, with a disposable-target guard."""

from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass
from urllib.parse import urlsplit

# Accepted only for a loopback/private address or a host carrying one of these
# tokens as a dot/hyphen part; anything else is treated as production and refused.
DISPOSABLE_TOKENS = frozenset({
    "test", "tests", "staging", "preprod", "sandbox", "qa", "local", "localhost",
})


class ProductionTargetRefused(RuntimeError):
    """Raised when the configured target cannot be proven disposable."""


def _host_is_private(host: str) -> bool:
    try:
        address = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False
    return address.is_loopback or address.is_private


def target_is_disposable(host: str) -> bool:
    """True when the host is demonstrably a throwaway test target."""
    host = host.lower()
    if not host:
        return False
    if _host_is_private(host):
        return True
    parts = {part for label in host.split(".") for part in label.split("-")}
    return bool(parts & DISPOSABLE_TOKENS)


@dataclass(frozen=True)
class LoadConfig:
    base_url: str
    origin: str
    password: str
    run_id: str
    email_domain: str = "load.invalid"
    accounts: int = 500
    users: int = 100
    sources: int = 100
    source_header: str = "X-Forwarded-For"
    warmup_s: int = 300
    ramp_s: int = 300
    plateau_s: int = 1200
    rampdown_s: int = 120
    think_min_s: float = 1.0
    think_max_s: float = 3.0
    seed: int = 20260101
    timeout_s: float = 15.0

    @property
    def host(self) -> str:
        return urlsplit(self.base_url).hostname or ""


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    return default if raw is None or not raw.strip() else int(raw)


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ProductionTargetRefused(f"{name} is required; the harness has no default")
    return value


def from_env() -> LoadConfig:
    """Build the run configuration, refusing anything that is not provably disposable."""
    config = LoadConfig(
        base_url=_required("Q02_TARGET_URL").rstrip("/"),
        origin=_required("Q02_ORIGIN").rstrip("/"),
        password=_required("Q02_SEED_PASSWORD"),
        run_id=_required("Q02_RUN_ID"),
        accounts=_int_env("Q02_ACCOUNTS", 500),
        users=_int_env("Q02_USERS", 100),
        sources=_int_env("Q02_SOURCES", 100),
        plateau_s=_int_env("Q02_PLATEAU_S", 1200),
        seed=_int_env("Q02_SEED", 20260101),
    )
    scheme = urlsplit(config.base_url).scheme
    if scheme not in {"http", "https"}:
        raise ProductionTargetRefused(f"unsupported scheme {scheme!r}")
    if not target_is_disposable(config.host):
        raise ProductionTargetRefused(
            f"{config.host!r} is not provably a test target; refusing to generate load"
        )
    if _required("Q02_TARGET_ACK").lower() != config.host.lower():
        raise ProductionTargetRefused("Q02_TARGET_ACK must repeat the target host exactly")
    return config
