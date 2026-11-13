"""The plateau request mix of docs/contracts/verification.md, Q02 section.

50% search, 25% public profile, 10% public contacts, 10% private reads,
5% owner profile PUT. Anonymous reads dominate because the product is a public
talent directory: a visitor searches, opens a few profiles and may reveal the
published contacts, while only the minority who own a profile ever write.
"""

from __future__ import annotations

import random
from collections.abc import Callable

from tests.load.config import LoadConfig
from tests.load.corpus import Account, profile_body
from tests.load.session import UserSession

MIX: tuple[tuple[str, int], ...] = (
    ("search", 50),
    ("public_profile", 25),
    ("public_contacts", 10),
    ("private_read", 10),
    ("profile_update", 5),
)


def mix_is_valid(mix: tuple[tuple[str, int], ...] = MIX) -> bool:
    return sum(weight for _, weight in mix) == 100


class Journeys:
    """Bound to one virtual user; holds the shared read-only corpus references."""

    def __init__(self, session: UserSession, config: LoadConfig,
                 profile_ids: list[str], skill_ids: list[str], terms: list[str]) -> None:
        self.session = session
        self.config = config
        self.profile_ids = profile_ids
        self.skill_ids = skill_ids
        self.terms = terms
        self.rng = random.Random(f"{config.seed}:{session.account.index}")

    def _profile_id(self) -> str:
        return self.rng.choice(self.profile_ids)

    def search(self) -> int:
        params: dict[str, str] = {"q": self.rng.choice(self.terms)}
        if self.rng.random() < 0.4:
            params["page"] = str(self.rng.randint(1, 3))
        if self.rng.random() < 0.3:
            params["availability"] = self.rng.choice(("immediate", "freelance"))
        return self.session.call("search", "GET", "/api/v1/search/profiles", params=params)

    def public_profile(self) -> int:
        return self.session.call(
            "public_profile", "GET", f"/api/v1/profiles/{self._profile_id()}")

    def public_contacts(self) -> int:
        return self.session.call(
            "public_contacts", "GET", f"/api/v1/profiles/{self._profile_id()}/contacts")

    def private_read(self) -> int:
        """Owner-side read: alternates between the profile and its portfolio list."""
        path = self.rng.choice(("/api/v1/profiles/me", "/api/v1/profiles/me/portfolio"))
        return self.session.call("private_read", "GET", path,
                                 headers={"Origin": self.config.origin})

    def profile_update(self) -> int:
        body = profile_body(self.session.account, self.skill_ids, self.config.seed)
        status = self.session.call("profile_update", "PUT", "/api/v1/profiles/me",
                                   json=body, headers=self.session.mutation_headers())
        if status == 403:
            self.session.refresh_csrf()
        return status

    def table(self) -> dict[str, Callable[[], int]]:
        return {
            "search": self.search,
            "public_profile": self.public_profile,
            "public_contacts": self.public_contacts,
            "private_read": self.private_read,
            "profile_update": self.profile_update,
        }

    def next_journey(self) -> Callable[[], int]:
        names = [name for name, weight in MIX for _ in range(weight)]
        return self.table()[self.rng.choice(names)]


def account_for(accounts: list[Account], slot: int) -> Account:
    """Virtual user ``slot`` borrows a distinct seeded account."""
    return accounts[slot % len(accounts)]
