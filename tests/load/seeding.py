"""Seeds the 500 synthetic accounts and profiles through the public API.

Registration is capped at 5/hour/IP (docs/contracts/http.md), so 500 accounts need
at least 100 distinct sources: the harness spends exactly the 5 registrations each
source is allowed. Seeding therefore depends on the same trusted-proxy setup as the
run itself and must be verified by ``tests/load/attribution.py`` first.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import httpx

from tests.load.config import LoadConfig
from tests.load.corpus import Account, accounts, profile_body

REGISTER_PER_SOURCE_PER_HOUR = 5


@dataclass
class SeedOutcome:
    created: list[Account]
    profile_ids: dict[str, str]
    refused: dict[int, int]

    @property
    def complete(self) -> bool:
        return len(self.profile_ids) == len(self.created)


def registration_budget(config: LoadConfig) -> int:
    """How many accounts the configured sources may legally register in one hour."""
    return config.sources * REGISTER_PER_SOURCE_PER_HOUR


def skill_ids(config: LoadConfig) -> list[str]:
    response = httpx.get(f"{config.base_url}/api/v1/skills",
                         params={"page_size": "50"}, timeout=config.timeout_s)
    response.raise_for_status()
    return [str(item["id"]) for item in response.json()["items"]]


def _headers(config: LoadConfig, account: Account, credential: bool) -> dict[str, str]:
    headers = {
        config.source_header: account.source,
        "Origin": config.origin,
        "Content-Type": "application/json",
    }
    if credential:
        headers["X-Auth-Intent"] = "session"
    return headers


def seed_account(config: LoadConfig, account: Account,
                 skills: list[str]) -> tuple[Account, str | None, int]:
    """register → login → PUT profile. Returns the profile id or the refusing status."""
    body = {"email": account.email, "password": account.password}
    with httpx.Client(base_url=config.base_url, timeout=config.timeout_s) as client:
        created = client.post("/api/v1/auth/register", json=body,
                              headers=_headers(config, account, True))
        if created.status_code not in (201, 409):
            return account, None, created.status_code
        logged = client.post("/api/v1/auth/login", json=body,
                             headers=_headers(config, account, True))
        if logged.status_code != 200:
            return account, None, logged.status_code
        csrf = client.get("/api/v1/auth/csrf",
                          headers=_headers(config, account, False)).json()["csrf_token"]
        headers = _headers(config, account, False) | {"X-CSRF-Token": csrf}
        written = client.put("/api/v1/profiles/me",
                             json=profile_body(account, skills, config.seed),
                             headers=headers)
        if written.status_code not in (200, 201):
            return account, None, written.status_code
        return account, str(written.json()["id"]), written.status_code


def seed(config: LoadConfig, workers: int = 10) -> SeedOutcome:
    """Seed the corpus; refuses to start when the source budget cannot cover it."""
    if config.accounts > registration_budget(config):
        raise RuntimeError(
            f"{config.accounts} accounts exceed the {registration_budget(config)} "
            f"registrations {config.sources} sources may make in one hour"
        )
    corpus = accounts(config)
    skills = skill_ids(config)
    outcome = SeedOutcome(created=corpus, profile_ids={}, refused={})
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for account, profile_id, status in pool.map(
                lambda item: seed_account(config, item, skills), corpus):
            if profile_id is None:
                outcome.refused[account.index] = status
            else:
                outcome.profile_ids[account.email] = profile_id
            time.sleep(0)
    return outcome
