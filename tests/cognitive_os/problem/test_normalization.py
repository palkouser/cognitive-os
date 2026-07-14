from uuid import uuid4

from cognitive_os.problem.normalization import MACHINE_CONSTRAINTS, normalize_problem


def test_normalization_is_stable_and_inserts_policy() -> None:
    task_id, task_run_id = uuid4(), uuid4()
    left = normalize_problem(
        task_id=task_id,
        task_run_id=task_run_id,
        title="Task",
        raw_request="  one\n two  ",
        repository_language_english=True,
    )
    right = normalize_problem(
        task_id=task_id,
        task_run_id=task_run_id,
        title="Task",
        raw_request="one two",
        repository_language_english=True,
    )
    assert left.request_hash == right.request_hash
    assert left.normalized_request == "one two"
    assert set(MACHINE_CONSTRAINTS) <= set(left.machine_constraints)
    assert any("English" in item for item in left.machine_constraints)
