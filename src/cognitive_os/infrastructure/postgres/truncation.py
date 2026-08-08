"""The one rule every truncating path obeys. Finding W7-F1.

Deliberately its own module, and deliberately importing nothing. The rule is a question about
the environment — was this database named for erasure? — and it has no database dependency at
all. Its first home was `engine.py`, which imports SQLAlchemy at module scope, and that broke a
credential-free CI lane that runs the learning suite without the PostgreSQL extra: a pure
environment check became unreachable wherever a driver was not installed. A guard nobody can
import is a guard nobody calls.

W6-F2 established the rule for the integration fixture and D4-W0-F1 established it for the
learned smoke, each in its own file, and each wrote that there were two truncating paths. There
were eleven. The other nine kept the older fence, "the database name ends in `_test`", which is
a naming convention rather than consent: every sprint's *evidence* database ends in `_test` too.
On 2026-08-07 a release-matrix run with the D4 environment sourced put `cognitive_os_s21d4_test`
in front of five of them, and they truncated 1,076 committed observations, 9 datasets and 18
artifact lineages. That store had a verified backup from three minutes earlier; D3's, erased the
same way in W0-F1, did not.

So there is one implementation and every truncating path calls it. A second mechanism answering
the same question differently is how an operator ends up knowing one fence and meeting the other.
`tests/cognitive_os/learning/test_truncation_fence.py` holds the list and fails when a twelfth
`TRUNCATE` appears without one.
"""

from __future__ import annotations

import os

#: The environment variable that nominates one database for erasure, by name.
TRUNCATABLE_DATABASE = "COGOS_TRUNCATABLE_DATABASE"


class TruncationNotNominated(RuntimeError):
    """Nobody nominated a database, so nobody asked for this. Usually a skip."""


class TruncationRefused(RuntimeError):
    """A database was nominated and a different one is connected. Always loud."""


def require_nominated_for_truncation(database: str) -> None:
    """Refuse to erase a database that was not named for erasure.

    Two outcomes, and they are different on purpose. Nothing nominated means nobody asked, and a
    whole-repository run should decline rather than break. A nomination naming another database
    means an operator meant one store and is connected to another, which has to be loud: the
    next statement would have been a `TRUNCATE`.
    """
    nominated = os.environ.get(TRUNCATABLE_DATABASE)
    if nominated is None:
        raise TruncationNotNominated(f"no database is nominated by {TRUNCATABLE_DATABASE}")
    if nominated != database:
        raise TruncationRefused(
            f"refusing to TRUNCATE {database}: {TRUNCATABLE_DATABASE} names {nominated}. "
            "Nominating one database and connecting to another is a misconfiguration, and the "
            "next statement would have been a TRUNCATE."
        )
