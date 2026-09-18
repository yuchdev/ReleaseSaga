import json
from pathlib import Path
from typing import Optional

import pytest

from release_saga.config import ReleaseConfig
from release_saga.steps.base import ReleaseStep
from release_saga.steps.git_tag import GitTagStep
from release_saga.steps.github_release import GitHubReleaseStep
from release_saga.steps.pypi_publish import PIP, PublishPyPiStep
from release_saga.steps.s3 import UploadS3Step


def make_config(project_dir: Path, **overrides: Optional[str]) -> ReleaseConfig:
    values = {
        "project_dir": project_dir,
        "package_name": "demo_package",
        "package_name_dash": "demo-package",
        "version": "1.2.3",
        "release_notes_path": "RELEASE_NOTES.json",
    }
    values.update(overrides)
    return ReleaseConfig(**values)


class _DummyStep(ReleaseStep):
    def execute(self):
        pass

    def rollback(self):
        pass


def test_release_step_default_check_returns_none():
    assert _DummyStep().check() is None


def test_upload_s3_step_reports_missing_bucket(tmp_path: Path):
    wheel = tmp_path / "demo_package-1.2.3-py3-none-any.whl"
    wheel.write_text("wheel", encoding="utf-8")

    step = UploadS3Step(make_config(tmp_path), wheel_path=wheel)

    assert step.check() == "no s3_bucket configured (set [tool.release-saga].s3_bucket or --s3-bucket)"


def test_upload_s3_step_reports_missing_awscli(tmp_path: Path, monkeypatch):
    wheel = tmp_path / "demo_package-1.2.3-py3-none-any.whl"
    wheel.write_text("wheel", encoding="utf-8")
    step = UploadS3Step(make_config(tmp_path, s3_bucket="bucket"), wheel_path=wheel)

    monkeypatch.setattr("release_saga.steps.s3.executable_exists", lambda executable: False)

    assert step.check() == "awscli not installed"


def test_upload_s3_step_reports_invalid_credentials(tmp_path: Path, monkeypatch):
    wheel = tmp_path / "demo_package-1.2.3-py3-none-any.whl"
    wheel.write_text("wheel", encoding="utf-8")
    step = UploadS3Step(make_config(tmp_path, s3_bucket="bucket"), wheel_path=wheel)

    monkeypatch.setattr("release_saga.steps.s3.executable_exists", lambda executable: True)
    monkeypatch.setattr("release_saga.steps.s3.command_ok", lambda cmd, cwd=None: False)

    assert step.check() == "aws credentials are not configured or not valid"


def test_upload_s3_step_reports_existing_object(tmp_path: Path, monkeypatch):
    wheel = tmp_path / "demo_package-1.2.3-py3-none-any.whl"
    wheel.write_text("wheel", encoding="utf-8")
    step = UploadS3Step(
        make_config(tmp_path, s3_bucket="bucket", s3_prefix="releases"),
        wheel_path=wheel,
    )

    monkeypatch.setattr("release_saga.steps.s3.executable_exists", lambda executable: True)

    def fake_command_ok(cmd, cwd=None):
        return cmd[:4] == ["aws", "sts", "get-caller-identity"] or cmd[:3] == [
            "aws",
            "s3api",
            "head-object",
        ]

    monkeypatch.setattr("release_saga.steps.s3.command_ok", fake_command_ok)

    expected = "S3 object 'releases/demo_package-1.2.3-py3-none-any.whl' already exists in bucket 'bucket'"

    assert step.check() == expected


def test_upload_s3_step_check_passes_when_object_absent(tmp_path: Path, monkeypatch):
    wheel = tmp_path / "demo_package-1.2.3-py3-none-any.whl"
    wheel.write_text("wheel", encoding="utf-8")
    step = UploadS3Step(
        make_config(tmp_path, s3_bucket="bucket", s3_prefix="releases"),
        wheel_path=wheel,
    )

    monkeypatch.setattr("release_saga.steps.s3.executable_exists", lambda executable: True)

    def fake_command_ok(cmd, cwd=None):
        return cmd[:4] == ["aws", "sts", "get-caller-identity"]

    monkeypatch.setattr("release_saga.steps.s3.command_ok", fake_command_ok)

    assert step.check() is None


def test_upload_s3_step_key_defaults_to_wheel_name_when_prefix_empty(tmp_path: Path):
    wheel = tmp_path / "demo_package-1.2.3-py3-none-any.whl"
    wheel.write_text("wheel", encoding="utf-8")
    step = UploadS3Step(
        make_config(tmp_path, s3_bucket="bucket", s3_prefix=""),
        wheel_path=wheel,
    )

    assert step._key() == wheel.name


def test_git_tag_step_reports_missing_git(tmp_path: Path, monkeypatch):
    step = GitTagStep(make_config(tmp_path))

    monkeypatch.setattr("release_saga.steps.git_tag.executable_exists", lambda executable: False)

    assert step.check() == "git not installed"


def test_git_tag_step_reports_missing_remote_when_git_exists(tmp_path: Path, monkeypatch):
    step = GitTagStep(make_config(tmp_path))

    monkeypatch.setattr("release_saga.steps.git_tag.executable_exists", lambda executable: True)
    monkeypatch.setattr("release_saga.steps.git_tag.command_ok", lambda cmd, cwd=None: False)

    assert step.check() == "no 'origin' remote configured for this repository"


def test_git_tag_step_reports_existing_local_tag(tmp_path: Path, monkeypatch):
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


def test_git_tag_step_reports_existing_remote_tag(tmp_path: Path, monkeypatch):
    step = GitTagStep(make_config(tmp_path))

    monkeypatch.setattr("release_saga.steps.git_tag.executable_exists", lambda executable: True)

    def fake_command_ok(cmd, cwd=None):
        return cmd[:4] == ["git", "remote", "get-url", "origin"] or cmd[:4] == [
            "git",
            "ls-remote",
            "--exit-code",
            "--tags",
        ]

    monkeypatch.setattr("release_saga.steps.git_tag.command_ok", fake_command_ok)

    assert step.check() == "git tag 'v1.2.3' already exists on remote 'origin'"


def test_git_tag_step_check_passes_when_tag_available(tmp_path: Path, monkeypatch):
    step = GitTagStep(make_config(tmp_path))

    monkeypatch.setattr("release_saga.steps.git_tag.executable_exists", lambda executable: True)
    monkeypatch.setattr(
        "release_saga.steps.git_tag.command_ok",
        lambda cmd, cwd=None: cmd[:4] == ["git", "remote", "get-url", "origin"],
    )

    assert step.check() is None


def test_git_tag_step_execute_creates_and_pushes_tag(tmp_path: Path, monkeypatch):
    step = GitTagStep(make_config(tmp_path))
    commands: list[list[str]] = []

    monkeypatch.setattr(
        "release_saga.steps.git_tag.run",
        lambda cmd, **kwargs: commands.append(cmd),
    )

    step.execute()

    assert commands == [
        ["git", "tag", "-a", "v1.2.3", "-m", "Release 1.2.3"],
        ["git", "push", "origin", "refs/tags/v1.2.3"],
    ]
    assert step._created_local_tag is True
    assert step._pushed_remote_tag is True


def test_git_tag_step_rollback_only_cleans_up_created_effects(tmp_path: Path, monkeypatch):
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


def test_github_release_step_reports_missing_gh_cli(tmp_path: Path, monkeypatch):
    step = GitHubReleaseStep(make_config(tmp_path))

    monkeypatch.setattr(
        "release_saga.steps.github_release.executable_exists",
        lambda executable: False,
    )

    assert step.check() == "GitHub CLI (gh) not installed"


def test_github_release_step_reports_not_logged_in(tmp_path: Path, monkeypatch):
    step = GitHubReleaseStep(make_config(tmp_path))

    monkeypatch.setattr(
        "release_saga.steps.github_release.executable_exists",
        lambda executable: True,
    )
    monkeypatch.setattr(
        "release_saga.steps.github_release.command_ok",
        lambda cmd, cwd=None: False,
    )

    assert step.check() == "gh is not logged in (run `gh auth login`)"


def test_github_release_step_reports_missing_release_notes_entry(
    tmp_path: Path,
    monkeypatch,
):
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


def test_github_release_step_reports_existing_release(tmp_path: Path, monkeypatch):
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


def test_github_release_step_check_passes_when_everything_available(
    tmp_path: Path,
    monkeypatch,
):
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
        return cmd[:3] == ["gh", "auth", "status"]

    monkeypatch.setattr("release_saga.steps.github_release.command_ok", fake_command_ok)

    assert step.check() is None


def test_tmp_release_notes_exits_when_version_missing(tmp_path: Path):
    (tmp_path / "RELEASE_NOTES.json").write_text(
        '{"release": {"download_link": ""}, "releases": {}}',
        encoding="utf-8",
    )
    step = GitHubReleaseStep(make_config(tmp_path))

    with pytest.raises(SystemExit) as exc_info:
        step.tmp_release_notes()

    assert exc_info.value.code == 1


def test_tmp_release_notes_writes_notes_and_download_link(tmp_path: Path):
    (tmp_path / "RELEASE_NOTES.json").write_text(
        json.dumps(
            {
                "release": {"download_link": "https://example.test/{package_name_dash}/{version}"},
                "releases": {"1.2.3": {"release_notes": ["Fixed a bug", "Added a feature"]}},
            }
        ),
        encoding="utf-8",
    )
    step = GitHubReleaseStep(make_config(tmp_path))

    notes_path = step.tmp_release_notes()
    try:
        content = notes_path.read_text(encoding="utf-8")
        assert "Fixed a bug" in content
        assert "Added a feature" in content
        assert "https://example.test/demo-package/1.2.3" in content
    finally:
        notes_path.unlink(missing_ok=True)


def test_github_release_step_execute_creates_release_and_cleans_up_notes_file(
    tmp_path: Path,
    monkeypatch,
):
    (tmp_path / "RELEASE_NOTES.json").write_text(
        json.dumps(
            {
                "release": {"download_link": "https://example.test/{package_name_dash}/{version}"},
                "releases": {"1.2.3": {"release_notes": ["Fixed a bug"]}},
            }
        ),
        encoding="utf-8",
    )
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "demo_package-1.2.3-py3-none-any.whl").write_text("wheel", encoding="utf-8")
    step = GitHubReleaseStep(make_config(tmp_path))
    commands: list[list[str]] = []

    monkeypatch.setattr(
        "release_saga.steps.github_release.run",
        lambda cmd, **kwargs: commands.append(cmd),
    )

    step.execute()

    assert step._created_release is True
    assert commands[0][:4] == ["gh", "release", "create", "v1.2.3"]
    notes_file_arg = Path(commands[0][commands[0].index("--notes-file") + 1])
    assert not notes_file_arg.exists()


def test_github_release_step_rollback_only_deletes_created_release(
    tmp_path: Path,
    monkeypatch,
):
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


def test_upload_s3_step_uses_normalized_object_key(tmp_path: Path, monkeypatch):
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


def test_upload_s3_step_strips_leading_slashes_from_prefix(tmp_path: Path):
    wheel = tmp_path / "demo_package-1.2.3-py3-none-any.whl"
    wheel.write_text("wheel", encoding="utf-8")
    step = UploadS3Step(
        make_config(tmp_path, s3_bucket="bucket", s3_prefix="/releases"),
        wheel_path=wheel,
    )

    assert step._key() == "releases/demo_package-1.2.3-py3-none-any.whl"


def test_publish_pypi_step_reports_missing_twine(tmp_path: Path, monkeypatch):
    step = PublishPyPiStep(make_config(tmp_path))

    monkeypatch.setattr(
        "release_saga.steps.pypi_publish.executable_exists",
        lambda executable: False,
    )

    assert step.check() == "twine not installed"


def test_publish_pypi_step_reports_missing_pypirc(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("HOME", str(tmp_path))
    step = PublishPyPiStep(make_config(tmp_path))

    monkeypatch.setattr(
        "release_saga.steps.pypi_publish.executable_exists",
        lambda executable: True,
    )

    assert step.check() == "no ~/.pypirc file found"


def test_publish_pypi_step_check_passes_when_pypirc_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".pypirc").write_text("", encoding="utf-8")
    step = PublishPyPiStep(make_config(tmp_path))

    monkeypatch.setattr(
        "release_saga.steps.pypi_publish.executable_exists",
        lambda executable: True,
    )

    assert step.check() is None


def test_publish_pypi_step_execute_raises_when_no_distributions(tmp_path: Path):
    step = PublishPyPiStep(make_config(tmp_path, publish_glob="dist/*"))

    with pytest.raises(FileNotFoundError):
        step.execute()


def test_publish_pypi_step_rollback_logs_manual_yank_warning(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    step = PublishPyPiStep(make_config(tmp_path))

    step.rollback()

    assert "cannot auto-rollback a PyPI publish" in capsys.readouterr().err


def test_publish_pypi_step_expands_distribution_glob(tmp_path: Path, monkeypatch):
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
