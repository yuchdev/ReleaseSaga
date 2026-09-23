import json
from pathlib import Path

import pytest

from release_saga.config import ReleaseConfig
from release_saga.history import RunHistory
from release_saga.pipeline import clean_release_run, run_release_pipeline
from release_saga.steps.base import ReleaseStep


class RecordingStep(ReleaseStep):
    name = "recording step"

    def __init__(self, events: list[str]):
        self.events = events

    def execute(self):
        self.events.append("execute")
        self.recovery_value = "after execute"

    def rollback(self):
        self.events.append("rollback")

    def recovery_data(self):
        return {"value": getattr(self, "recovery_value", "before execute")}

    def prepare_rollback(self, recovery_data):
        self.events.append(f"prepare:{recovery_data['value']}")


class FailingRecoveryStep(RecordingStep):
    def execute(self):
        super().execute()
        self._raise_during_recovery = True

    def recovery_data(self):
        if getattr(self, "_raise_during_recovery", False):
            raise RuntimeError("cannot capture recovery data")
        return super().recovery_data()


def make_config(project_dir: Path) -> ReleaseConfig:
    return ReleaseConfig(
        project_dir=project_dir,
        package_name="demo_package",
        package_name_dash="demo-package",
        version="1.2.3",
    )


def test_pipeline_persists_completed_run(tmp_path: Path, monkeypatch):
    """[Unit] pipeline: persists each completed release run."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    config = make_config(tmp_path)

    run_release_pipeline([RecordingStep([])], config)

    records = list((tmp_path / "data" / "release-saga" / "demo-package" / "1.2.3").glob("*.json"))
    assert len(records) == 1
    data = json.loads(records[0].read_text(encoding="utf-8"))
    assert data["status"] == "completed"
    assert data["steps"][0]["status"] == "completed"
    assert data["steps"][0]["recovery_data"] == {"value": "after execute"}


def test_clean_release_run_rolls_back_completed_steps_in_reverse(tmp_path: Path, monkeypatch):
    """[Unit] clean pipeline: restores and rolls back completed steps in reverse order."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    config = make_config(tmp_path)
    events: list[str] = []
    first = RecordingStep(events)
    second = RecordingStep(events)
    history = RunHistory.create(config, [first, second])
    history.set_step_status(0, "completed")
    history.set_step_status(1, "completed")

    clean_release_run([first, second], history)

    assert events == ["prepare:before execute", "prepare:before execute", "rollback", "rollback"]
    assert history.data["status"] == "rolled_back"
    assert [step["status"] for step in history.data["steps"]] == ["rolled_back", "rolled_back"]


def test_clean_release_run_rolls_back_in_progress_steps_in_reverse(tmp_path: Path, monkeypatch):
    """[Unit] clean pipeline: restores and rolls back uncertain in-progress steps in reverse order."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    config = make_config(tmp_path)
    events: list[str] = []
    first = RecordingStep(events)
    second = RecordingStep(events)
    history = RunHistory.create(config, [first, second])
    history.set_step_status(0, "completed")
    history.set_step_status(1, "in_progress")

    clean_release_run([first, second], history)

    assert events == ["prepare:before execute", "prepare:before execute", "rollback", "rollback"]
    assert history.data["status"] == "rolled_back"
    assert [step["status"] for step in history.data["steps"]] == ["rolled_back", "rolled_back"]


def test_latest_incomplete_ignores_successful_runs(tmp_path: Path, monkeypatch):
    """[Unit] run history: returns only the newest recoverable run."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    config = make_config(tmp_path)
    completed = RunHistory.create(config, [RecordingStep([])])
    completed.set_status("completed")
    interrupted = RunHistory.create(config, [RecordingStep([])])

    loaded = RunHistory.latest_incomplete(config)

    assert loaded is not None
    assert loaded.data["run_id"] == interrupted.data["run_id"]


def test_latest_incomplete_ignores_other_project_with_same_name_and_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Unit] run history: does not recover an unrelated project with matching metadata."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    other_config = make_config(tmp_path / "other-project")
    RunHistory.create(other_config, [RecordingStep([])])

    loaded = RunHistory.latest_incomplete(make_config(tmp_path / "current-project"))

    assert loaded is None


def test_pipeline_rolls_back_when_recovery_data_capture_fails(tmp_path: Path, monkeypatch):
    """[Unit] pipeline: recovery-data capture failures still trigger rollback."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    config = make_config(tmp_path)
    events: list[str] = []

    with pytest.raises(SystemExit):
        run_release_pipeline([RecordingStep(events), FailingRecoveryStep(events)], config)

    records = list((tmp_path / "data" / "release-saga" / "demo-package" / "1.2.3").glob("*.json"))
    assert len(records) == 1
    data = json.loads(records[0].read_text(encoding="utf-8"))
    assert events == ["execute", "execute", "rollback", "rollback"]
    assert data["status"] == "rolled_back"
    assert [step["status"] for step in data["steps"]] == ["rolled_back", "rolled_back"]
