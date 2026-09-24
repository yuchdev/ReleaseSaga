from pathlib import Path
from typing import Optional

import pytest

from release_saga.cli import build_release_steps
from release_saga.config import ReleaseConfig
from release_saga.steps.git_tag import GitTagStep
from release_saga.steps.github_release import GitHubReleaseStep
from release_saga.steps.local_install import LocalInstallStep
from release_saga.steps.pypi_publish import PublishPyPiStep
from release_saga.steps.s3 import UploadS3Step


def make_config(project_dir: Path, **overrides: Optional[str]) -> ReleaseConfig:
    values = {
        "project_dir": project_dir,
        "package_name": "demo_package",
        "package_name_dash": "demo-package",
        "version": "1.2.3",
    }
    values.update(overrides)
    return ReleaseConfig(**values)


def write_wheel(project_dir: Path):
    dist_dir = project_dir / "dist"
    dist_dir.mkdir(exist_ok=True)
    (dist_dir / "demo_package-1.2.3-py3-none-any.whl").write_text("wheel", encoding="utf-8")


def test_build_release_steps_no_flags_returns_empty_list(tmp_path: Path):
    """[Unit] build_release_steps: no flags returns an empty step list.

    Scenario:
        Focus on the `no flags returns an empty step list` case for `build_release_steps` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `build_release_steps` branch for this case and the fixtures or monkeypatches that establish it.
    """
    steps = build_release_steps(
        make_config(tmp_path),
        upload_s3=False,
        create_release=False,
        publish_pypi=False,
    )

    assert steps == []


def test_build_release_steps_upload_s3_only(tmp_path: Path):
    """[Unit] build_release_steps: upload S3 flag adds only the upload step.

    Scenario:
        Focus on the `upload S3 flag adds only the upload step` case for `build_release_steps` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `build_release_steps` branch for this case and the fixtures or monkeypatches that establish it.
    """
    write_wheel(tmp_path)

    steps = build_release_steps(
        make_config(tmp_path),
        upload_s3=True,
        create_release=False,
        publish_pypi=False,
    )

    assert len(steps) == 1
    assert isinstance(steps[0], UploadS3Step)


def test_build_release_steps_create_release_only(tmp_path: Path):
    """[Unit] build_release_steps: create release flag adds tag and release steps.

    Scenario:
        Focus on the `create release flag adds tag and release steps` case for `build_release_steps` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `build_release_steps` branch for this case and the fixtures or monkeypatches that establish it.
    """
    steps = build_release_steps(
        make_config(tmp_path),
        upload_s3=False,
        create_release=True,
        publish_pypi=False,
    )

    assert len(steps) == 2
    assert isinstance(steps[0], GitTagStep)
    assert isinstance(steps[1], GitHubReleaseStep)


def test_build_release_steps_publish_pypi_only(tmp_path: Path):
    """[Unit] build_release_steps: publish PyPI flag adds only the publish step.

    Scenario:
        Focus on the `publish PyPI flag adds only the publish step` case for `build_release_steps` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `build_release_steps` branch for this case and the fixtures or monkeypatches that establish it.
    """
    steps = build_release_steps(
        make_config(tmp_path),
        upload_s3=False,
        create_release=False,
        publish_pypi=True,
    )

    assert len(steps) == 1
    assert isinstance(steps[0], PublishPyPiStep)


def test_build_release_steps_inserts_plugin_steps_before_pypi(tmp_path: Path):
    """[Unit] build_release_steps: plugin steps run after built-ins, before PyPI publish.

    Scenario:
        Focus on the `plugin steps run after built-ins, before PyPI publish` case for `build_release_steps` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `build_release_steps` branch for this case and the fixtures or monkeypatches that establish it.
    """
    class FakePluginStep:
        pass

    plugin_step = FakePluginStep()
    steps = build_release_steps(
        make_config(tmp_path),
        upload_s3=False,
        create_release=True,
        publish_pypi=True,
        plugin_steps=[plugin_step],
    )

    assert isinstance(steps[0], GitTagStep)
    assert isinstance(steps[1], GitHubReleaseStep)
    assert steps[2] is plugin_step
    assert isinstance(steps[3], PublishPyPiStep)


def test_build_release_steps_all_flags_full_order(tmp_path: Path):
    """[Unit] build_release_steps: all flags preserve the full step order.

    Scenario:
        Focus on the `all flags preserve the full step order` case for `build_release_steps` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `build_release_steps` branch for this case and the fixtures or monkeypatches that establish it.
    """
    write_wheel(tmp_path)

    steps = build_release_steps(
        make_config(tmp_path),
        upload_s3=True,
        create_release=True,
        publish_pypi=True,
        local_install=True,
    )

    assert [type(step) for step in steps] == [
        LocalInstallStep,
        UploadS3Step,
        GitTagStep,
        GitHubReleaseStep,
        PublishPyPiStep,
    ]


@pytest.mark.parametrize(
    ("local_install", "local_dev_mode", "expected_dev_mode"),
    [(True, False, False), (False, True, True), (True, True, True)],
)
def test_build_release_steps_local_install_runs_first(
    tmp_path: Path,
    local_install: bool,
    local_dev_mode: bool,
    expected_dev_mode: bool,
):
    """[Unit] build_release_steps: local install runs first.

    Scenario:
        Focus on the `local install runs first` case for `build_release_steps` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `build_release_steps` branch for this case and the fixtures or monkeypatches that establish it.
    """
    write_wheel(tmp_path)

    steps = build_release_steps(
        make_config(tmp_path),
        upload_s3=True,
        create_release=False,
        publish_pypi=False,
        local_install=local_install,
        local_dev_mode=local_dev_mode,
    )

    assert [type(step) for step in steps] == [LocalInstallStep, UploadS3Step]
    assert steps[0].dev_mode is expected_dev_mode
