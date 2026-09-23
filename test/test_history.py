import json
from pathlib import Path

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

    def rollback(self):
        self.events.append("rollback")

    def recovery_data(self):
        return {"value": "persisted"}

    def prepare_rollback(self, recovery_data):
        self.events.append(f"prepare:{recovery_data['value']}")


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
    assert data["steps"][0]["recovery_data"] == {"value": "persisted"}


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

    assert events == ["prepare:persisted", "prepare:persisted", "rollback", "rollback"]
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
