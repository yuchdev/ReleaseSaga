from subprocess import CalledProcessError

import pytest

from release_saga.pipeline import run_release_pipeline
from release_saga.steps.base import ReleaseStep


class DummyStep(ReleaseStep):
    def __init__(
        self,
        name: str,
        events: list[str],
        *,
        check_result: str | None = None,
        execute_error: Exception | None = None,
    ):
        self.name = name
        self.events = events
        self._check_result = check_result
        self._execute_error = execute_error

    def check(self) -> str | None:
        self.events.append(f"check:{self.name}")
        return self._check_result

    def execute(self) -> None:
        self.events.append(f"execute:{self.name}")
        if self._execute_error is not None:
            raise self._execute_error

    def rollback(self) -> None:
        self.events.append(f"rollback:{self.name}")


def test_run_release_pipeline_rolls_back_failed_step_and_completed_steps() -> None:
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


def test_run_release_pipeline_rolls_back_completed_steps_when_next_step_unavailable() -> None:
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
