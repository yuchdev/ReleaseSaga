import importlib
from importlib.metadata import PackageNotFoundError

import pytest

import release_saga
import release_saga.cli
import release_saga.config
import release_saga.pipeline
import release_saga.steps
import release_saga.steps.git_tag
import release_saga.steps.github_release
import release_saga.steps.pypi_publish
import release_saga.steps.s3


def test_public_api_reexports_match_source_modules():
    assert release_saga.ReleaseStep is release_saga.steps.base.ReleaseStep
    assert release_saga.ReleaseConfig is release_saga.config.ReleaseConfig
    assert release_saga.load_config is release_saga.config.load_config
    assert release_saga.resolve_project_dir is release_saga.config.resolve_project_dir
    assert release_saga.run_release_pipeline is release_saga.pipeline.run_release_pipeline
    assert release_saga.build_arg_parser is release_saga.cli.build_arg_parser
    assert release_saga.build_release_steps is release_saga.cli.build_release_steps


def test_public_api_keeps_version():
    assert isinstance(release_saga.__version__, str)


def test_version_falls_back_when_package_metadata_missing(
    monkeypatch: pytest.MonkeyPatch,
):
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
    assert release_saga.steps.GitTagStep is release_saga.steps.git_tag.GitTagStep
    assert release_saga.steps.GitHubReleaseStep is release_saga.steps.github_release.GitHubReleaseStep
    assert release_saga.steps.PublishPyPiStep is release_saga.steps.pypi_publish.PublishPyPiStep
    assert release_saga.steps.UploadS3Step is release_saga.steps.s3.UploadS3Step
