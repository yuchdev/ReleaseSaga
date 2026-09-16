from pathlib import Path

from release_saga.config import ReleaseConfig
from release_saga.steps.git_tag import GitTagStep
from release_saga.steps.github_release import GitHubReleaseStep
from release_saga.steps.pypi_publish import PIP, PublishPyPiStep
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


def test_git_tag_step_reports_existing_local_tag(tmp_path: Path, monkeypatch) -> None:
    step = GitTagStep(make_config(tmp_path))

    monkeypatch.setattr("release_saga.steps.git_tag.executable_exists", lambda executable: True)

    def fake_command_ok(cmd, cwd=None):
        return cmd[:4] == ["git", "remote", "get-url", "origin"] or cmd[:3] == [
            "git",
            "rev-parse",
            "-q",
        ]

    monkeypatch.setattr("release_saga.steps.git_tag.command_ok", fake_command_ok)

    assert step.check() == "git tag 'v1.2.3' already exists locally"


def test_git_tag_step_rollback_only_cleans_up_created_effects(tmp_path: Path, monkeypatch) -> None:
    step = GitTagStep(make_config(tmp_path))
    commands: list[list[str]] = []

    monkeypatch.setattr(
        "release_saga.steps.git_tag.run",
        lambda cmd, **kwargs: commands.append(cmd),
    )

    step.rollback()
    step._created_local_tag = True
    step.rollback()
    step._pushed_remote_tag = True
    step.rollback()

    assert commands == [
        ["git", "tag", "-d", "v1.2.3"],
        ["git", "push", "origin", ":refs/tags/v1.2.3"],
        ["git", "tag", "-d", "v1.2.3"],
    ]


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
    def fake_command_ok(cmd, cwd=None):
        return cmd[:3] == ["gh", "auth", "status"]

    monkeypatch.setattr("release_saga.steps.github_release.command_ok", fake_command_ok)

    assert step.check() == "no release notes found for version 1.2.3 in RELEASE_NOTES.json"


def test_publish_pypi_step_reports_missing_twine(tmp_path: Path, monkeypatch) -> None:
    step = PublishPyPiStep(make_config(tmp_path))

    monkeypatch.setattr(
        "release_saga.steps.pypi_publish.executable_exists",
        lambda executable: False,
    )

    assert step.check() == "twine not installed"


def test_github_release_step_reports_existing_release(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "RELEASE_NOTES.json").write_text(
        '{"release": {"download_link": ""}, "releases": {"1.2.3": {"release_notes": []}}}',
        encoding="utf-8",
    )
    step = GitHubReleaseStep(make_config(tmp_path))

    monkeypatch.setattr(
        "release_saga.steps.github_release.executable_exists",
        lambda executable: True,
    )

    def fake_command_ok(cmd, cwd=None):
        return cmd[:3] == ["gh", "auth", "status"] or cmd[:3] == ["gh", "release", "view"]

    monkeypatch.setattr("release_saga.steps.github_release.command_ok", fake_command_ok)

    assert step.check() == "GitHub release 'v1.2.3' already exists"


def test_github_release_step_rollback_only_deletes_created_release(
    tmp_path: Path,
    monkeypatch,
) -> None:
    step = GitHubReleaseStep(make_config(tmp_path))
    commands: list[list[str]] = []

    monkeypatch.setattr(
        "release_saga.steps.github_release.run",
        lambda cmd, **kwargs: commands.append(cmd),
    )

    step.rollback()
    step._created_release = True
    step.rollback()

    assert commands == [["gh", "release", "delete", "v1.2.3", "--yes"]]


def test_upload_s3_step_uses_normalized_object_key(tmp_path: Path, monkeypatch) -> None:
    wheel = tmp_path / "demo_package-1.2.3-py3-none-any.whl"
    wheel.write_text("wheel", encoding="utf-8")
    step = UploadS3Step(
        make_config(tmp_path, s3_bucket="bucket", s3_prefix="releases"),
        wheel_path=wheel,
    )
    commands: list[list[str]] = []

    monkeypatch.setattr(
        "release_saga.steps.s3.run",
        lambda cmd, **kwargs: commands.append(cmd),
    )

    step.execute()
    step.rollback()

    assert commands == [
        [
            "aws",
            "s3",
            "cp",
            str(wheel),
            "s3://bucket/releases/demo_package-1.2.3-py3-none-any.whl",
            "--acl",
            "public-read",
        ],
        [
            "aws",
            "s3",
            "rm",
            "s3://bucket/releases/demo_package-1.2.3-py3-none-any.whl",
        ],
    ]


def test_publish_pypi_step_expands_distribution_glob(tmp_path: Path, monkeypatch) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    wheel = dist_dir / "demo_package-1.2.3-py3-none-any.whl"
    tarball = dist_dir / "demo_package-1.2.3.tar.gz"
    wheel.write_text("wheel", encoding="utf-8")
    tarball.write_text("sdist", encoding="utf-8")
    step = PublishPyPiStep(make_config(tmp_path, publish_glob="dist/*"))
    commands: list[list[str]] = []

    monkeypatch.setattr(
        "release_saga.steps.pypi_publish.run",
        lambda cmd, **kwargs: commands.append(cmd),
    )

    step.execute()

    assert commands == [
        [*PIP, "install", "--upgrade", "build", "twine"],
        ["twine", "check", str(wheel), str(tarball)],
        ["twine", "upload", str(wheel), str(tarball)],
    ]
