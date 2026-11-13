"""The virtual-user pool that executes the schedule of ``tests/load/phases.py``."""

from __future__ import annotations

import random
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from tests.load.config import LoadConfig
from tests.load.corpus import Account, accounts, search_terms
from tests.load.journeys import Journeys, account_for
from tests.load.metrics import Recorder
from tests.load.phases import Phases, phases_of
from tests.load.session import LoginRefused, UserSession


@dataclass
class RunResult:
    plateau: Recorder = field(default_factory=Recorder)
    whole_run: Recorder = field(default_factory=Recorder)
    plateau_duration_s: float = 0.0
    login_failures: int = 0


def _virtual_user(config: LoadConfig, slot: int, corpus: list[Account],
                  profile_ids: list[str], skills: list[str], result: RunResult,
                  phases: Phases, started: float) -> None:
    """One virtual user: login once, then journeys with think time until the end."""
    session = UserSession(config, account_for(corpus, slot), result.whole_run, started)
    rng = random.Random(f"{config.seed}:think:{slot}")
    terms = search_terms(config)
    try:
        session.login()
    except LoginRefused:
        result.login_failures += 1
        session.close()
        return
    try:
        while (elapsed := time.monotonic() - started) < phases.total_s:
            if phases.active_users(elapsed, config.users) <= slot:
                time.sleep(1.0)
                continue
            plateau = phases.in_plateau(elapsed)
            session.recorder = result.plateau if plateau else result.whole_run
            Journeys(session, config, profile_ids, skills, terms).next_journey()()
            time.sleep(rng.uniform(config.think_min_s, config.think_max_s))
    finally:
        session.close()


def run(config: LoadConfig, profile_ids: list[str], skills: list[str]) -> RunResult:
    """Execute the schedule. Blocking; the caller owns seeding and reporting."""
    phases, corpus = phases_of(config), accounts(config)
    result = RunResult(plateau_duration_s=float(phases.plateau_s))
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=config.users) as pool:
        for slot in range(config.users):
            pool.submit(_virtual_user, config, slot, corpus, profile_ids,
                        skills, result, phases, started)
    return result
