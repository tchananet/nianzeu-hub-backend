"""Preflight: prove the target attributes IP quotas per synthetic source.

Without this proof the 100 virtual users share one quota key and the run measures
its own rate limiting instead of the service. The probe deliberately burns one
source's public-read quota (120/min/IP) and then checks a *second* source is still
served. A 429 for the second source means the forwarded address is not trusted:
abort, fix ``FORWARDED_ALLOW_IPS`` on the authorised test proxy, and start over.

This module also implements the separate refusal-path scenario A01 asks for: a
single source, 429 expected, thresholds not applicable.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from tests.load.config import LoadConfig

PUBLIC_READS_PER_MINUTE = 120
PROBE_PATH = "/api/v1/skills"


@dataclass(frozen=True)
class AttributionResult:
    burned_source: str
    control_source: str
    burn_statuses: dict[int, int]
    control_status: int

    @property
    def quota_reached(self) -> bool:
        return self.burn_statuses.get(429, 0) > 0

    @property
    def per_source(self) -> bool:
        """True only when one source was throttled and another remained served."""
        return self.quota_reached and self.control_status == 200

    def verdict(self) -> str:
        if not self.quota_reached:
            return "inconclusive: the burn source was never throttled"
        return "per-source" if self.per_source else "shared: forwarded address ignored"


def _get(config: LoadConfig, client: httpx.Client, source: str) -> int:
    response = client.get(PROBE_PATH, headers={config.source_header: source})
    return response.status_code


def probe(config: LoadConfig, burn_source: str = "203.0.113.250",
          control_source: str = "203.0.113.251") -> AttributionResult:
    """Burn one source's public-read quota, then test a control source."""
    statuses: dict[int, int] = {}
    with httpx.Client(base_url=config.base_url, timeout=config.timeout_s) as client:
        for _ in range(PUBLIC_READS_PER_MINUTE + 5):
            status = _get(config, client, burn_source)
            statuses[status] = statuses.get(status, 0) + 1
            if status == 429:
                break
        control = _get(config, client, control_source)
    return AttributionResult(burn_source, control_source, statuses, control)


def require_per_source(config: LoadConfig) -> AttributionResult:
    result = probe(config)
    if not result.per_source:
        raise RuntimeError(
            "quota attribution is not per-source (" + result.verdict() + "); a load run "
            "from here would measure rate limiting, not capacity"
        )
    return result


def refusal_scenario(config: LoadConfig, source: str = "203.0.113.252",
                     attempts: int = PUBLIC_READS_PER_MINUTE + 20) -> dict[int, int]:
    """Deliberate quota scenario: one source, N+1 refused with Retry-After.

    Reported separately from the plateau run. Its 429s are expected, so the A01
    error-rate threshold does not apply to it.
    """
    statuses: dict[int, int] = {}
    with httpx.Client(base_url=config.base_url, timeout=config.timeout_s) as client:
        for _ in range(attempts):
            response = client.get(PROBE_PATH, headers={config.source_header: source})
            statuses[response.status_code] = statuses.get(response.status_code, 0) + 1
            if response.status_code == 429:
                assert response.headers.get("retry-after", "").isdigit(), "Retry-After"
    return statuses
