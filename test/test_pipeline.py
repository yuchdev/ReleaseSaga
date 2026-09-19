from subprocess import CalledProcessError
from typing import Optional

import pytest

from release_saga.pipeline import run_release_pipeline
from release_saga.steps.base import ReleaseStep


class DummyStep(ReleaseStep):
    def __init__(
        self,
        name: str,
        events: list[str],
        *,
        check_result: Optional[str] = None,
        check_error: Optional[Exception] = None,
        execute_error: Optional[Exception] = None,
        rollback_error: Optional[Exception] = None,
    ):
        self.name = name
        self.events = events
        self._check_result = check_result
        self._check_error = check_error
        self._execute_error = execute_error
        self._rollback_error = rollback_error

    def check(self) -> Optional[str]:
        self.events.append(f"check:{self.name}")
        if self._check_error is not None:
            raise self._check_error
        return self._check_result

    def execute(self):
        self.events.append(f"execute:{self.name}")
        if self._execute_error is not None:
            raise self._execute_error

    def rollback(self):
        self.events.append(f"rollback:{self.name}")
        if self._rollback_error is not None:
            raise self._rollback_error


def test_run_release_pipeline_completes_all_steps_successfully():
    """[Unit] run_release_pipeline: completes all steps successfully.

    Scenario:
        Focus on the `completes all steps successfully` case for `run_release_pipeline` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `run_release_pipeline` branch for this case and the fixtures or monkeypatches that establish it.
    """
    events: list[str] = []
    first = DummyStep("first", events)
    second = DummyStep("second", events)

    run_release_pipeline([first, second])

    assert events == [
        "check:first",
        "execute:first",
        "check:second",
        "execute:second",
    ]


def test_run_release_pipeline_rolls_back_failed_step_and_completed_steps():
    """[Unit] run_release_pipeline: rolls back failed step and completed steps.

    Scenario:
        Focus on the `rolls back failed step and completed steps` case for `run_release_pipeline` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `run_release_pipeline` branch for this case and the fixtures or monkeypatches that establish it.
    """
    events: list[str] = []
    first = DummyStep("first", events)
    second = DummyStep("second", events, execute_error=CalledProcessError(1, ["cmd"]))

    with pytest.raises(SystemExit):
        run_release_pipeline([first, second])

    assert events == [
        "check:first",
        "execute:first",
        "check:second",
        "execute:second",
        "rollback:second",
        "rollback:first",
    ]


def test_run_release_pipeline_generic_execute_exception_triggers_rollback():
    """[Unit] run_release_pipeline: generic execute exception triggers rollback.

    Scenario:
        Focus on the `generic execute exception triggers rollback` case for `run_release_pipeline` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `run_release_pipeline` branch for this case and the fixtures or monkeypatches that establish it.
    """
    events: list[str] = []
    first = DummyStep("first", events)
    second = DummyStep("second", events, execute_error=RuntimeError("boom"))

    with pytest.raises(SystemExit):
        run_release_pipeline([first, second])

    assert events == [
        "check:first",
        "execute:first",
        "check:second",
        "execute:second",
        "rollback:second",
        "rollback:first",
    ]


def test_run_release_pipeline_continues_rollback_when_a_rollback_itself_fails():
    """[Unit] run_release_pipeline: continues rollback when a rollback itself fails.

    Scenario:
        Focus on the `continues rollback when a rollback itself fails` case for `run_release_pipeline` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `run_release_pipeline` branch for this case and the fixtures or monkeypatches that establish it.
    """
    events: list[str] = []
    first = DummyStep("first", events, rollback_error=RuntimeError("cleanup failed"))
    second = DummyStep("second", events, execute_error=RuntimeError("boom"))

    with pytest.raises(SystemExit):
        run_release_pipeline([first, second])

    assert events == [
        "check:first",
        "execute:first",
        "check:second",
        "execute:second",
        "rollback:second",
        "rollback:first",
    ]


def test_run_release_pipeline_rolls_back_completed_steps_when_next_step_unavailable():
    """[Unit] run_release_pipeline: rolls back completed steps when next step unavailable.

    Scenario:
        Focus on the `rolls back completed steps when next step unavailable` case for `run_release_pipeline` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `run_release_pipeline` branch for this case and the fixtures or monkeypatches that establish it.
    """
    events: list[str] = []
    first = DummyStep("first", events)
    second = DummyStep("second", events, check_result="missing credentials")

    with pytest.raises(SystemExit):
        run_release_pipeline([first, second])

    assert events == [
        "check:first",
        "execute:first",
        "check:second",
        "rollback:first",
    ]


def test_run_release_pipeline_rolls_back_completed_steps_when_check_raises():
    """[Unit] run_release_pipeline: rolls back completed steps when check raises.

    Scenario:
        Focus on the `rolls back completed steps when check raises` case for `run_release_pipeline` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `run_release_pipeline` branch for this case and the fixtures or monkeypatches that establish it.
    """
    events: list[str] = []
    first = DummyStep("first", events)
    second = DummyStep("second", events, check_error=RuntimeError("bad release notes"))

    with pytest.raises(SystemExit):
        run_release_pipeline([first, second])

    assert events == [
        "check:first",
        "execute:first",
        "check:second",
        "rollback:first",
    ]
