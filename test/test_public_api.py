import importlib
from importlib.metadata import PackageNotFoundError

import pytest

import release_saga
import release_saga.cli
import release_saga.config
import release_saga.pipeline
import release_saga.plugins
import release_saga.steps
import release_saga.steps.git_tag
import release_saga.steps.github_release
import release_saga.steps.pypi_publish
import release_saga.steps.s3


def test_public_api_reexports_match_source_modules():
    """[Unit] public_api: reexports match source modules.

    Scenario:
        Focus on the `reexports match source modules` case for `public_api` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `public_api` branch for this case and the fixtures or monkeypatches that establish it.
    """
    assert release_saga.ReleaseStep is release_saga.steps.base.ReleaseStep
    assert release_saga.ReleaseConfig is release_saga.config.ReleaseConfig
    assert release_saga.load_config is release_saga.config.load_config
    assert release_saga.resolve_project_dir is release_saga.config.resolve_project_dir
    assert release_saga.run_release_pipeline is release_saga.pipeline.run_release_pipeline
    assert release_saga.build_arg_parser is release_saga.cli.build_arg_parser
    assert release_saga.build_release_steps is release_saga.cli.build_release_steps
    assert release_saga.PluginLoadError is release_saga.plugins.PluginLoadError
    assert release_saga.load_plugin_steps is release_saga.plugins.load_plugin_steps
    assert release_saga.load_configured_steps is release_saga.plugins.load_configured_steps
    assert release_saga.discover_entry_point_steps is release_saga.plugins.discover_entry_point_steps
    assert release_saga.resolve_plugin_spec is release_saga.plugins.resolve_plugin_spec


def test_public_api_keeps_version():
    """[Unit] __version__: export stays a string.

    Scenario:
        Focus on the `export stays a string` case for `__version__` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `__version__` branch for this case and the fixtures or monkeypatches that establish it.
    """
    assert isinstance(release_saga.__version__, str)


def test_version_falls_back_when_package_metadata_missing(
    monkeypatch: pytest.MonkeyPatch,
):
    """[Unit] __version__: falls back when package metadata is missing.

    Scenario:
        Focus on the `falls back when package metadata is missing` case for `__version__` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `__version__` branch for this case and the fixtures or monkeypatches that establish it.
    """
    def raise_not_found(name: str):
        raise PackageNotFoundError(name)

    monkeypatch.setattr("importlib.metadata.version", raise_not_found)
    importlib.reload(release_saga)

    try:
        assert release_saga.__version__ == "0.9.0"
    finally:
        monkeypatch.undo()
        importlib.reload(release_saga)


def test_steps_package_reexports_concrete_steps():
    """[Unit] steps_package: reexports concrete step classes.

    Scenario:
        Focus on the `reexports concrete step classes` case for `steps_package` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `steps_package` branch for this case and the fixtures or monkeypatches that establish it.
    """
    assert release_saga.steps.GitTagStep is release_saga.steps.git_tag.GitTagStep
    assert release_saga.steps.GitHubReleaseStep is release_saga.steps.github_release.GitHubReleaseStep
    assert release_saga.steps.LocalInstallStep is release_saga.steps.local_install.LocalInstallStep
    assert release_saga.steps.PublishPyPiStep is release_saga.steps.pypi_publish.PublishPyPiStep
    assert release_saga.steps.UploadS3Step is release_saga.steps.s3.UploadS3Step
