"""S22B-W3: mutation and recovery at scale, and the one thing a crash left behind.

W3 decides the last of the five exit criteria — that a restore reproduces everything — so the
questions here are about whether the mutations were real, whether the crash was real, and
whether the restore was checked against the store as it actually ended up:

*Did the mutations go through the governed path?* A wave that wrote statuses directly would
produce the same counts and none of the history. Every transition has to have left a revision
and an event, and the arithmetic between the three active-view readings has to close.

*Can the active view notice a desync?* §2.2e asks for it queried rather than counted, so the
driver asks two independent questions — the item's own status column, and the status on the
revision its `current_revision` names — and this asserts they agreed at every checkpoint. Two
readings that agree are evidence; one reading is a hope.

*Was the crash a crash?* The database was killed with SIGKILL mid-ingest, not the writer. The
record has to show a dead writer, a recovered server, and the integrity questions asked
afterwards — including the one that came back non-zero.

*Was the restore checked against the mutated store?* The counts in the checklist must be the
post-mutation, post-crash ones. A restore verified against W1's numbers would be verifying a
store that no longer exists.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-22/evidence"

MUTATIONS = EVIDENCE / "sprint-22b-w3-mutations.json"
CRASH = EVIDENCE / "sprint-22b-w3-crash.json"
BLOAT = EVIDENCE / "sprint-22b-w3-bloat-reindex.json"
RESTORE = EVIDENCE / "sprint-22b-w3-restore-checklist.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_the_mutation_waves_ran_through_the_governed_lifecycle() -> None:
    """Not a status update: a revision, a provenance carry-over and an event per transition."""
    record = _load(MUTATIONS)
    waves = {wave["wave"]: wave for wave in record["waves"]}
    assert set(waves) == {"supersession", "tombstone"}
    for wave in waves.values():
        assert "MemoryLifecycleService" in wave["path"], wave["wave"]
        assert wave["failure_count"] == 0, wave["failures"]
        assert wave["items_mutated"] == wave["items_requested"]
        assert wave["reads_an_exit_criterion"] is False


def test_a_supersession_costs_two_transitions_because_the_released_table_says_so() -> None:
    """candidate -> superseded is not legal; candidate -> verified -> superseded is.

    The promotion is not a detail: it is the released path refusing to let a driver skip a
    state, and the count is asserted so a future shortcut cannot pass unnoticed.
    """
    waves = {wave["wave"]: wave for wave in _load(MUTATIONS)["waves"]}
    supersession = waves["supersession"]
    assert supersession["promotions"] == supersession["items_mutated"]
    assert supersession["transitions"] == 2 * supersession["items_mutated"]
    tombstone = waves["tombstone"]
    assert tombstone["promotions"] == 0
    assert tombstone["transitions"] == tombstone["items_mutated"]


def test_the_active_view_was_queried_two_ways_that_agreed_at_every_checkpoint() -> None:
    """22A W4-F2 in the shape W3 needs it: a claim that must be able to notice a change."""
    record = _load(MUTATIONS)
    views = record["active_view"]
    assert set(views) == {"before", "after_supersessions", "after_tombstones"}
    for name, view in views.items():
        assert view["queried_not_counted"] is True, name
        assert view["the_two_readings_agree"] is True, name
        assert view["active_rows_by_item_status"] == view["active_rows_by_current_revision_join"], (
            name
        )
    assert record["both_readings_agree_throughout"] is True


def test_the_active_view_moved_by_exactly_what_the_waves_mutated() -> None:
    record = _load(MUTATIONS)
    views = record["active_view"]
    waves = {wave["wave"]: wave for wave in record["waves"]}
    before = views["before"]["active_rows_by_item_status"]
    middle = views["after_supersessions"]["active_rows_by_item_status"]
    after = views["after_tombstones"]["active_rows_by_item_status"]
    assert before - middle == waves["supersession"]["items_mutated"]
    assert middle - after == waves["tombstone"]["items_mutated"]
    assert after == record["expected_active_rows_after"]
    assert record["active_view_matches_the_mutations"] is True


def test_every_transition_left_a_revision_and_an_event() -> None:
    """Fifteen thousand transitions, fifteen thousand revisions, fifteen thousand events."""
    views = _load(MUTATIONS)["active_view"]
    transitions = sum(wave["transitions"] for wave in _load(MUTATIONS)["waves"])
    assert views["after_tombstones"]["revisions"] - views["before"]["revisions"] == transitions
    assert views["after_tombstones"]["events"] - views["before"]["events"] == transitions


def test_the_crash_killed_the_database_and_the_writer_died_with_it() -> None:
    """A crash test whose writer exits cleanly did not crash anything."""
    record = _load(CRASH)
    assert "SIGKILL" in record["what_was_killed"]
    assert record["writer_exit_code"] != 0
    assert record["database_recovered"] is True
    assert record["items_written_before_the_kill"] >= 1
    assert record["recovery_seconds"] > 0


def test_no_item_lost_the_revision_it_was_written_with() -> None:
    """Both are one transaction. This asserts the transaction is real rather than assumed."""
    assert _load(CRASH)["items_missing_their_current_revision"] == 0


def test_the_crash_left_exactly_one_item_outside_its_own_event_stream() -> None:
    """W3-F1, asserted as measured rather than as hoped.

    `MemoryService.create` commits the record and then appends the event in a *separate*
    transaction, so an unclean stop in that window leaves a governed item with no
    `memory.item_created` event. One item landed in it. The number is asserted exactly, because
    zero would be a different finding and two would be a different measurement — and because a
    released write path that closed this window would make this test fail, which is the correct
    way for it to fail.
    """
    assert _load(CRASH)["items_missing_an_event"] == 1


def test_the_resumed_ingest_duplicated_nothing() -> None:
    """The idempotency key turns a re-created item into a lookup, so a resume is safe."""
    record = _load(CRASH)
    assert record["resume_duplicated_nothing"] is True
    assert record["items_after_resume"] == record["expected_items_after_resume"]


def test_the_reindex_ran_with_readers_and_measured_them_throughout() -> None:
    """A reindex that is only timed proves the reindex finished, which nobody asked."""
    reindex = _load(BLOAT)["reindex_with_readers"]
    assert reindex["concurrent_readers"] >= 1
    assert reindex["reader_queries"] > 0
    assert reindex["reindex_seconds"] > 0
    assert reindex["readers_saw_an_error"] is False
    assert reindex["reader_latency"] is not None


def test_the_readers_read_through_the_index_that_was_being_rebuilt() -> None:
    """W3-F2. A counting scan beside the index answers a question nobody asked.

    The first run measured 408 065 counting queries during the rebuild — real readers, real
    latencies, and no information about whether approximate retrieval survives its own index
    being rebuilt. That is the only thing this measurement is for.
    """
    reindex = _load(BLOAT)["reindex_with_readers"]
    assert reindex["readers_read_through_the_index"] is True
    assert "ANN" in reindex["reader_query"]


def test_the_bloat_was_measured_before_autovacuum_could_erase_it() -> None:
    """W3-F3. Bloat measured ninety minutes late is a measurement of autovacuum.

    The first run reported 0.00 % dead tuples on every governed table, which was true and
    uninformative: the mutation waves had run an hour and a half earlier. A wave now runs
    immediately before the measurement, in the same process, with nothing in between.
    """
    record = _load(BLOAT)
    assert record["bloat_measured_before_autovacuum_could_run"] is True
    wave = record["mutation_wave_immediately_before"]
    assert wave is not None
    assert wave["failure_count"] == 0
    assert wave["items_mutated"] > 0


def test_the_reindex_was_run_on_the_dataset_no_exit_reads() -> None:
    """W1-F6's rule, stated ahead of the mistake: a rebuild replaces what was measured."""
    record = _load(BLOAT)
    assert record["dataset"] == "uniform"
    assert record["reads_an_exit_criterion"] is False
    assert "clustered" in record["why_this_dataset"]


def test_the_restore_checklist_was_verified_against_the_mutated_store() -> None:
    """The W3 exit. Verified by query and by loading bytes, on the store as it ended up."""
    record = _load(RESTORE)
    assert record["all_four_met"] is True
    assert all(record["checks"].values()), record["checks"]
    assert record["verified_by_query_not_by_digest"] is True
    assert record["artifact_loaded_from_restored_archive"]["matches_expected"] is True
    # Source against restored, both queried at check time. Comparing the restored view to the
    # *mutations* record instead would have passed here by arithmetic accident — the crash
    # resume added five thousand active items and the bloat wave superseded five thousand,
    # which happens to land back on the same number.
    assert record["restored"]["active_view_rows"] == record["source"]["active_view_rows"]
    assert record["source"]["row_counts"] == record["restored"]["row_counts"]


def test_the_restored_store_is_the_one_the_whole_wave_left_behind() -> None:
    """Bigger than W1's on every count, because W3 mutated, crashed and resumed on top of it."""
    counts = _load(RESTORE)["restored"]["row_counts"]
    assert counts["memory_items"] > 50_040
    assert counts["memory_revisions"] > counts["memory_items"]
    assert counts["events"] >= counts["memory_revisions"]


@pytest.mark.parametrize("path", [MUTATIONS, CRASH, BLOAT, RESTORE])
def test_every_w3_record_binds_the_recipes_it_was_measured_under(path: Path) -> None:
    record = _load(path)
    assert (
        record["recipes_hash"]
        == _load(EVIDENCE / "sprint-22b-pre-registration.json")["recipes_hash"]
    )
