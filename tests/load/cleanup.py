"""Removal of the synthetic corpus. Prints SQL by default; never guesses a target.

Every seeded account carries the ``q02-<run_id>-`` email prefix, so removal is one
statement whose blast radius is visible before anyone runs it. The harness does not
execute it: deleting rows on a host is the operator's decision, and ``app/`` plus
the production database are outside this mission's ownership.
"""

from __future__ import annotations

import re
import sys

SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,31}$")

TEMPLATE = """\
-- Q02 load corpus removal, run_id = {run_id}
-- Review the count first, then delete. Profiles, contacts, portfolio items and
-- sessions follow by cascade (see docs/contracts/data.md).
SELECT count(*) FROM users WHERE email LIKE 'q02-{run_id}-%';
DELETE FROM users WHERE email LIKE 'q02-{run_id}-%';
-- Quota windows keyed by the synthetic sources expire on their own within 24 h.
"""


def removal_sql(run_id: str) -> str:
    if SAFE_RUN_ID.fullmatch(run_id) is None:
        raise ValueError("run_id must match [A-Za-z0-9][A-Za-z0-9.-]{0,31}: no SQL metacharacters")
    return TEMPLATE.format(run_id=run_id)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m tests.load.cleanup <run_id>", file=sys.stderr)
        return 2
    print(removal_sql(argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
