"""Deterministic synthetic corpus: 500 accounts and their profile payloads.

Every value derives from ``LoadConfig.seed`` and ``LoadConfig.run_id``, so a run is
reproducible and its residue is identifiable by the ``q02-<run_id>-`` email prefix.
No real person, address or credential appears here.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from tests.load.config import LoadConfig

CITIES = ("Douala", "Yaounde", "Bafoussam", "Garoua", "Bamenda", "Kribi")
AVAILABILITY = ("immediate", "1-week", "freelance", "full-time")
LEVELS = ("junior", "intermediate", "senior")
UNITS = ("hour", "day", "project")


@dataclass(frozen=True)
class Account:
    index: int
    email: str
    password: str
    source: str
    """Synthetic client address this account always presents, see docs/qa/load.md."""


def source_address(index: int) -> str:
    """One address per synthetic source, inside TEST-NET-3 (RFC 5737)."""
    return f"203.0.113.{1 + index % 254}"


def accounts(config: LoadConfig) -> list[Account]:
    return [
        Account(
            index=index,
            email=f"q02-{config.run_id}-{index:04d}@{config.email_domain}",
            password=config.password,
            source=source_address(index % config.sources),
        )
        for index in range(config.accounts)
    ]


def profile_body(account: Account, skill_ids: list[str], seed: int) -> dict[str, object]:
    """A valid ProfileWrite payload per docs/contracts/profiles.md, all contacts public."""
    rng = random.Random(f"{seed}:{account.index}")
    chosen = rng.sample(skill_ids, min(3, len(skill_ids))) if skill_ids else []
    return {
        "display_name": f"Q02 Talent {account.index:04d}",
        "headline": f"Synthetic load profile {account.index:04d}",
        "bio": "Synthetic Q02 corpus entry. " * rng.randint(2, 20),
        "city": rng.choice(CITIES),
        "country_code": "CM",
        "availability": rng.choice(AVAILABILITY),
        "experience_level": rng.choice(LEVELS),
        "rate": {
            "amount": f"{rng.randrange(5, 200) * 1000}.00",
            "currency": "XAF",
            "unit": rng.choice(UNITS),
        },
        "skill_ids": chosen,
        "experiences": [{
            "title": "Synthetic engagement",
            "organization": f"Q02 Studio {account.index:04d}",
            "start_date": "2022-01-03",
            "end_date": None,
            "description": "Generated for the Q02 load corpus.",
        }],
        "certifications": [],
        "contacts": {
            "email": account.email,
            "phone": f"+2376{account.index:08d}"[:15],
            "whatsapp": None,
            "email_visible": True,
            "phone_visible": rng.random() < 0.5,
            "whatsapp_visible": False,
        },
    }


def search_terms(config: LoadConfig) -> list[str]:
    """Query strings a realistic visitor would type, drawn from the seeded corpus."""
    rng = random.Random(f"{config.seed}:terms")
    terms = ["talent", "synthetic", "load", "q02", *CITIES]
    terms += [f"Q02 Talent {rng.randrange(config.accounts):04d}" for _ in range(20)]
    return terms
