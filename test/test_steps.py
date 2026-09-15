from pathlib import Path

from release_saga.config import ReleaseConfig
from release_saga.steps.git_tag import GitTagStep
from release_saga.steps.github_release import GitHubReleaseStep
from release_saga.steps.pypi_publish import PublishPyPiStep
from release_saga.steps.s3 import UploadS3Step


def make_config(project_dir: Path, **overrides: str | None) -> ReleaseConfig:
    values = {
        "project_dir": project_dir,
        "package_name": "demo_package",
        "package_name_dash": "demo-package",
        "version": "1.2.3",
        "release_notes_path": "RELEASE_NOTES.json",
    }
    values.update(overrides)
    return ReleaseConfig(**values)


def test_upload_s3_step_reports_missing_bucket(tmp_path: Path) -> None:
    wheel = tmp_path / "demo_package-1.2.3-py3-none-any.whl"
    wheel.write_text("wheel", encoding="utf-8")

    step = UploadS3Step(make_config(tmp_path), wheel_path=wheel)

    assert (
        step.check() == "no s3_bucket configured (set [tool.release-saga].s3_bucket or --s3-bucket)"
    )


def test_git_tag_step_reports_missing_remote_when_git_exists(tmp_path: Path, monkeypatch) -> None:
    step = GitTagStep(make_config(tmp_path))

    monkeypatch.setattr("release_saga.steps.git_tag.executable_exists", lambda executable: True)
    monkeypatch.setattr("release_saga.steps.git_tag.command_ok", lambda cmd, cwd=None: False)

    assert step.check() == "no 'origin' remote configured for this repository"


def test_github_release_step_reports_missing_release_notes_entry(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "RELEASE_NOTES.json").write_text(
        '{"release": {"download_link": ""}, "releases": {}}',
        encoding="utf-8",
    )
    step = GitHubReleaseStep(make_config(tmp_path))

    monkeypatch.setattr(
        "release_saga.steps.github_release.executable_exists",
        lambda executable: True,
    )
    monkeypatch.setattr("release_saga.steps.github_release.command_ok", lambda cmd: True)

    assert step.check() == "no release notes found for version 1.2.3 in RELEASE_NOTES.json"


def test_publish_pypi_step_reports_missing_twine(tmp_path: Path, monkeypatch) -> None:
    step = PublishPyPiStep(make_config(tmp_path))

    monkeypatch.setattr(
        "release_saga.steps.pypi_publish.executable_exists",
        lambda executable: False,
    )

    assert step.check() == "twine not installed"
