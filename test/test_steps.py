import json
from pathlib import Path
from typing import Optional

import pytest

from release_saga.config import ReleaseConfig
from release_saga.steps.base import ReleaseStep
from release_saga.steps.git_tag import GitTagStep
from release_saga.steps.github_release import GitHubReleaseStep
from release_saga.steps.local_install import LocalInstallStep
from release_saga.steps.pypi_publish import PIP, PublishPyPiStep
from release_saga.steps.s3 import UploadS3Step


@pytest.fixture(autouse=True)
def _no_pip_bootstrap(monkeypatch: pytest.MonkeyPatch):
    """Keep the PyPI step from probing or bootstrapping the real interpreter's pip."""
    monkeypatch.setattr("release_saga.steps.pypi_publish.ensure_pip", lambda: None)


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
    """[Unit] release_step: default check returns none.

    Scenario:
        Focus on the `default check returns none` case for `release_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `release_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
    assert _DummyStep().check() is None


def test_upload_s3_step_reports_missing_bucket(tmp_path: Path):
    """[Unit] upload_s3_step: reports missing bucket.

    Scenario:
        Focus on the `reports missing bucket` case for `upload_s3_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `upload_s3_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
    wheel = tmp_path / "demo_package-1.2.3-py3-none-any.whl"
    wheel.write_text("wheel", encoding="utf-8")

    step = UploadS3Step(make_config(tmp_path), wheel_path=wheel)

    assert step.check() == "no s3_bucket configured (set [tool.release-saga].s3_bucket or --s3-bucket)"


def test_upload_s3_step_reports_missing_awscli(tmp_path: Path, monkeypatch):
    """[Unit] upload_s3_step: reports missing AWS CLI.

    Scenario:
        Focus on the `reports missing AWS CLI` case for `upload_s3_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `upload_s3_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
    wheel = tmp_path / "demo_package-1.2.3-py3-none-any.whl"
    wheel.write_text("wheel", encoding="utf-8")
    step = UploadS3Step(make_config(tmp_path, s3_bucket="bucket"), wheel_path=wheel)

    monkeypatch.setattr("release_saga.steps.s3.executable_exists", lambda executable: False)

    assert step.check() == "awscli not installed"


def test_upload_s3_step_reports_invalid_credentials(tmp_path: Path, monkeypatch):
    """[Unit] upload_s3_step: reports invalid credentials.

    Scenario:
        Focus on the `reports invalid credentials` case for `upload_s3_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `upload_s3_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
    wheel = tmp_path / "demo_package-1.2.3-py3-none-any.whl"
    wheel.write_text("wheel", encoding="utf-8")
    step = UploadS3Step(make_config(tmp_path, s3_bucket="bucket"), wheel_path=wheel)

    monkeypatch.setattr("release_saga.steps.s3.executable_exists", lambda executable: True)
    monkeypatch.setattr("release_saga.steps.s3.command_ok", lambda cmd, cwd=None: False)

    assert step.check() == "aws credentials are not configured or not valid"


def test_upload_s3_step_reports_existing_object(tmp_path: Path, monkeypatch):
    """[Unit] upload_s3_step: reports existing object.

    Scenario:
        Focus on the `reports existing object` case for `upload_s3_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `upload_s3_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
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
    """[Unit] upload_s3_step: check passes when object absent.

    Scenario:
        Focus on the `check passes when object absent` case for `upload_s3_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `upload_s3_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
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
    """[Unit] upload_s3_step: key defaults to wheel name when prefix empty.

    Scenario:
        Focus on the `key defaults to wheel name when prefix empty` case for `upload_s3_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `upload_s3_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
    wheel = tmp_path / "demo_package-1.2.3-py3-none-any.whl"
    wheel.write_text("wheel", encoding="utf-8")
    step = UploadS3Step(
        make_config(tmp_path, s3_bucket="bucket", s3_prefix=""),
        wheel_path=wheel,
    )

    assert step._key() == wheel.name


def test_git_tag_step_reports_missing_git(tmp_path: Path, monkeypatch):
    """[Unit] git_tag_step: reports missing git.

    Scenario:
        Focus on the `reports missing git` case for `git_tag_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `git_tag_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
    step = GitTagStep(make_config(tmp_path))

    monkeypatch.setattr("release_saga.steps.git_tag.executable_exists", lambda executable: False)

    assert step.check() == "git not installed"


def test_git_tag_step_reports_missing_remote_when_git_exists(tmp_path: Path, monkeypatch):
    """[Unit] git_tag_step: reports missing remote when git exists.

    Scenario:
        Focus on the `reports missing remote when git exists` case for `git_tag_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `git_tag_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
    step = GitTagStep(make_config(tmp_path))

    monkeypatch.setattr("release_saga.steps.git_tag.executable_exists", lambda executable: True)
    monkeypatch.setattr("release_saga.steps.git_tag.command_ok", lambda cmd, cwd=None: False)

    assert step.check() == "no 'origin' remote configured for this repository"


def test_git_tag_step_reports_existing_local_tag(tmp_path: Path, monkeypatch):
    """[Unit] git_tag_step: reports existing local tag.

    Scenario:
        Focus on the `reports existing local tag` case for `git_tag_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `git_tag_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
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
    """[Unit] git_tag_step: reports existing remote tag.

    Scenario:
        Focus on the `reports existing remote tag` case for `git_tag_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `git_tag_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
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
    """[Unit] git_tag_step: check passes when tag available.

    Scenario:
        Focus on the `check passes when tag available` case for `git_tag_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `git_tag_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
    step = GitTagStep(make_config(tmp_path))

    monkeypatch.setattr("release_saga.steps.git_tag.executable_exists", lambda executable: True)
    monkeypatch.setattr(
        "release_saga.steps.git_tag.command_ok",
        lambda cmd, cwd=None: cmd[:4] == ["git", "remote", "get-url", "origin"],
    )

    assert step.check() is None


def test_git_tag_step_execute_creates_and_pushes_tag(tmp_path: Path, monkeypatch):
    """[Unit] git_tag_step: execute creates and pushes tag.

    Scenario:
        Focus on the `execute creates and pushes tag` case for `git_tag_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `git_tag_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
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
    """[Unit] git_tag_step: rollback only cleans up created effects.

    Scenario:
        Focus on the `rollback only cleans up created effects` case for `git_tag_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `git_tag_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
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


def test_git_tag_step_uncertain_recovery_skips_missing_tag_artifacts(tmp_path: Path, monkeypatch):
    """[Unit] git_tag_step: uncertain recovery skips missing local and remote tags."""
    step = GitTagStep(make_config(tmp_path))
    commands: list[list[str]] = []

    monkeypatch.setattr("release_saga.steps.git_tag.command_ok", lambda cmd, cwd=None: False)
    monkeypatch.setattr(
        "release_saga.steps.git_tag.run",
        lambda cmd, **kwargs: commands.append(cmd),
    )

    step.prepare_recovery({"tag": "v1.2.3", "remote": "origin"}, "in_progress")
    step.rollback()

    assert commands == []


def test_github_release_step_reports_missing_gh_cli(tmp_path: Path, monkeypatch):
    """[Unit] github_release_step: reports missing gh CLI.

    Scenario:
        Focus on the `reports missing gh CLI` case for `github_release_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `github_release_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
    step = GitHubReleaseStep(make_config(tmp_path))

    monkeypatch.setattr(
        "release_saga.steps.github_release.executable_exists",
        lambda executable: False,
    )

    assert step.check() == "GitHub CLI (gh) not installed"


def test_github_release_step_reports_not_logged_in(tmp_path: Path, monkeypatch):
    """[Unit] github_release_step: reports not logged in.

    Scenario:
        Focus on the `reports not logged in` case for `github_release_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `github_release_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
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
    """[Unit] github_release_step: reports missing release notes entry.

    Scenario:
        Focus on the `reports missing release notes entry` case for `github_release_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `github_release_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
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
    """[Unit] github_release_step: reports existing release.

    Scenario:
        Focus on the `reports existing release` case for `github_release_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `github_release_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
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
    """[Unit] github_release_step: check passes when everything available.

    Scenario:
        Focus on the `check passes when everything available` case for `github_release_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `github_release_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
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
    """[Unit] tmp_release_notes: exits when version missing.

    Scenario:
        Focus on the `exits when version missing` case for `tmp_release_notes` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `tmp_release_notes` branch for this case and the fixtures or monkeypatches that establish it.
    """
    (tmp_path / "RELEASE_NOTES.json").write_text(
        '{"release": {"download_link": ""}, "releases": {}}',
        encoding="utf-8",
    )
    step = GitHubReleaseStep(make_config(tmp_path))

    with pytest.raises(SystemExit) as exc_info:
        step.tmp_release_notes()

    assert exc_info.value.code == 1


def test_tmp_release_notes_writes_notes_and_download_link(tmp_path: Path):
    """[Unit] tmp_release_notes: writes notes and download link.

    Scenario:
        Focus on the `writes notes and download link` case for `tmp_release_notes` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `tmp_release_notes` branch for this case and the fixtures or monkeypatches that establish it.
    """
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
    """[Unit] github_release_step: execute creates release and cleans up notes file.

    Scenario:
        Focus on the `execute creates release and cleans up notes file` case for `github_release_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `github_release_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
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
    """[Unit] github_release_step: rollback only deletes created release.

    Scenario:
        Focus on the `rollback only deletes created release` case for `github_release_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `github_release_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
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


def test_github_release_step_uncertain_recovery_skips_missing_release(tmp_path: Path, monkeypatch):
    """[Unit] github_release_step: uncertain recovery skips a missing release."""
    step = GitHubReleaseStep(make_config(tmp_path))
    commands: list[list[str]] = []

    monkeypatch.setattr("release_saga.steps.github_release.command_ok", lambda cmd, cwd=None: False)
    monkeypatch.setattr(
        "release_saga.steps.github_release.run",
        lambda cmd, **kwargs: commands.append(cmd),
    )

    step.prepare_recovery({"tag": "v1.2.3"}, "in_progress")
    step.rollback()

    assert commands == []


def test_upload_s3_step_uses_normalized_object_key(tmp_path: Path, monkeypatch):
    """[Unit] upload_s3_step: uses normalized object key.

    Scenario:
        Focus on the `uses normalized object key` case for `upload_s3_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `upload_s3_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
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
    """[Unit] upload_s3_step: strips leading slashes from prefix.

    Scenario:
        Focus on the `strips leading slashes from prefix` case for `upload_s3_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `upload_s3_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
    wheel = tmp_path / "demo_package-1.2.3-py3-none-any.whl"
    wheel.write_text("wheel", encoding="utf-8")
    step = UploadS3Step(
        make_config(tmp_path, s3_bucket="bucket", s3_prefix="/releases"),
        wheel_path=wheel,
    )

    assert step._key() == "releases/demo_package-1.2.3-py3-none-any.whl"


def test_publish_pypi_step_reports_missing_twine(tmp_path: Path, monkeypatch):
    """[Unit] publish_pypi_step: reports missing twine.

    Scenario:
        Focus on the `reports missing twine` case for `publish_pypi_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `publish_pypi_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
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
    """[Unit] publish_pypi_step: reports missing .pypirc.

    Scenario:
        Focus on the `reports missing .pypirc` case for `publish_pypi_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `publish_pypi_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
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
    """[Unit] publish_pypi_step: check passes when .pypirc exists.

    Scenario:
        Focus on the `check passes when .pypirc exists` case for `publish_pypi_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `publish_pypi_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".pypirc").write_text("", encoding="utf-8")
    step = PublishPyPiStep(make_config(tmp_path))

    monkeypatch.setattr(
        "release_saga.steps.pypi_publish.executable_exists",
        lambda executable: True,
    )

    assert step.check() is None


def test_publish_pypi_step_execute_raises_when_no_distributions(tmp_path: Path):
    """[Unit] publish_pypi_step: execute raises when no distributions.

    Scenario:
        Focus on the `execute raises when no distributions` case for `publish_pypi_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `publish_pypi_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
    step = PublishPyPiStep(make_config(tmp_path, publish_glob="dist/*"))

    with pytest.raises(FileNotFoundError):
        step.execute()


def test_publish_pypi_step_rollback_logs_manual_yank_warning(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    """[Unit] publish_pypi_step: rollback logs manual yank warning.

    Scenario:
        Focus on the `rollback logs manual yank warning` case for `publish_pypi_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `publish_pypi_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
    step = PublishPyPiStep(make_config(tmp_path))

    step.rollback()

    assert "cannot auto-rollback a PyPI publish" in capsys.readouterr().err


def test_publish_pypi_step_expands_distribution_glob(tmp_path: Path, monkeypatch):
    """[Unit] publish_pypi_step: expands distribution glob.

    Scenario:
        Focus on the `expands distribution glob` case for `publish_pypi_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `publish_pypi_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
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


def _write_wheel(project_dir: Path):
    dist_dir = project_dir / "dist"
    dist_dir.mkdir(exist_ok=True)
    (dist_dir / "demo_package-1.2.3-py3-none-any.whl").write_text("wheel", encoding="utf-8")


def test_local_install_step_reports_missing_wheel(tmp_path: Path):
    """[Unit] local_install_step: reports missing wheel.

    Scenario:
        Focus on the `reports missing wheel` case for `local_install_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `local_install_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
    reason = LocalInstallStep(make_config(tmp_path)).check()

    assert reason is not None
    assert "demo_package-1.2.3-" in reason


def test_local_install_step_dev_mode_check_skips_wheel_lookup(tmp_path: Path):
    """[Unit] local_install_step: dev mode check skips wheel lookup.

    Scenario:
        Focus on the `dev mode check skips wheel lookup` case for `local_install_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `local_install_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
    step = LocalInstallStep(make_config(tmp_path), dev_mode=True)

    assert step.check() is None
    assert step.name == "install package locally (development mode)"


def test_local_install_step_installs_then_uninstalls_on_rollback(tmp_path: Path, monkeypatch):
    """[Unit] local_install_step: installs then uninstalls on rollback.

    Scenario:
        Focus on the `installs then uninstalls on rollback` case for `local_install_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `local_install_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
    _write_wheel(tmp_path)
    calls: list[str] = []
    monkeypatch.setattr("release_saga.steps.local_install.install_wheel", lambda config: calls.append("install"))
    monkeypatch.setattr("release_saga.steps.local_install.uninstall_wheel", lambda config: calls.append("uninstall"))
    step = LocalInstallStep(make_config(tmp_path))

    assert step.check() is None
    step.execute()
    step.rollback()

    assert calls == ["install", "uninstall"]


def test_local_install_step_rollback_skips_uninstall_when_install_failed(tmp_path: Path, monkeypatch):
    """[Unit] local_install_step: rollback skips uninstall when install failed.

    Scenario:
        Focus on the `rollback skips uninstall when install failed` case for `local_install_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `local_install_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
    calls: list[str] = []

    def failing_install(config):
        raise RuntimeError("pip failed")

    monkeypatch.setattr("release_saga.steps.local_install.install_wheel", failing_install)
    monkeypatch.setattr("release_saga.steps.local_install.uninstall_wheel", lambda config: calls.append("uninstall"))
    step = LocalInstallStep(make_config(tmp_path))

    with pytest.raises(RuntimeError):
        step.execute()
    step.rollback()

    assert calls == []


def test_local_install_step_dev_mode_keeps_editable_install_on_rollback(
    tmp_path: Path,
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
):
    """[Unit] local_install_step: dev mode keeps editable install on rollback.

    Scenario:
        Focus on the `dev mode keeps editable install on rollback` case for `local_install_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `local_install_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
    calls: list[str] = []
    monkeypatch.setattr("release_saga.steps.local_install.install_wheel_devmode", lambda config: calls.append("editable"))
    monkeypatch.setattr("release_saga.steps.local_install.uninstall_wheel", lambda config: calls.append("uninstall"))
    step = LocalInstallStep(make_config(tmp_path), dev_mode=True)

    step.execute()
    step.rollback()

    assert calls == ["editable"]
    stderr = capsys.readouterr().err
    assert "Development in progress" in stderr
    assert "keeping editable install" in stderr


@pytest.mark.parametrize(
    ("status", "installed", "expected"),
    [
        ("completed", False, ["uninstall"]),
        ("in_progress", True, ["uninstall"]),
        ("in_progress", False, []),
    ],
)
def test_local_install_step_recovery_uninstalls_recorded_install(
    tmp_path: Path,
    monkeypatch,
    status: str,
    installed: bool,
    expected: list[str],
):
    """[Unit] local_install_step: recovery uninstalls recorded install.

    Scenario:
        Focus on the `recovery uninstalls recorded install` case for `local_install_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `local_install_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
    calls: list[str] = []
    monkeypatch.setattr("release_saga.steps.local_install.command_ok", lambda cmd, cwd=None: installed)
    monkeypatch.setattr("release_saga.steps.local_install.uninstall_wheel", lambda config: calls.append("uninstall"))
    original = LocalInstallStep(make_config(tmp_path))
    step = LocalInstallStep(make_config(tmp_path))

    step.prepare_recovery(original.recovery_data(), status)
    step.rollback()

    assert original.recovery_data() == {"dev_mode": False}
    assert calls == expected


def test_local_install_step_recovery_restores_dev_mode(tmp_path: Path, monkeypatch):
    """[Unit] local_install_step: recovery restores dev mode.

    Scenario:
        Focus on the `recovery restores dev mode` case for `local_install_step` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `local_install_step` branch for this case and the fixtures or monkeypatches that establish it.
    """
    calls: list[str] = []
    monkeypatch.setattr("release_saga.steps.local_install.uninstall_wheel", lambda config: calls.append("uninstall"))
    step = LocalInstallStep(make_config(tmp_path))

    step.prepare_recovery({"dev_mode": True}, "completed")
    step.rollback()

    assert step.dev_mode is True
    assert calls == []
