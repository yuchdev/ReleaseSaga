import runpy
import sys
from pathlib import Path

import pytest

from release_saga import cli
from release_saga.steps.base import ReleaseStep
from release_saga.steps.local_install import LocalInstallStep


def write_project(project_dir: Path, name: str = "demo-package"):
    (project_dir / "src" / name.replace("-", "_")).mkdir(parents=True)
    (project_dir / "pyproject.toml").write_text(
        f"""
[project]
name = "{name}"
version = "1.2.3"
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_help_lists_release_flags(capsys: pytest.CaptureFixture[str]):
    """[Unit] cli: help lists release flags.

    Scenario:
        Focus on the `help lists release flags` case for `cli` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `cli` branch for this case and the fixtures or monkeypatches that establish it.
    """
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--help"])

    assert exc_info.value.code == 0
    help_text = capsys.readouterr().out
    assert "--project-dir" in help_text
    assert "--wheel-glob" in help_text
    assert "--publish-glob" in help_text
    assert "--s3-bucket" in help_text
    assert "--git-tag-template" in help_text
    assert "--release-notes-path" in help_text
    assert "--version" in help_text
    assert "--set-version" in help_text
    assert "--clean" in help_text
    assert "--local-install" in help_text
    assert "--local-dev-mode" in help_text
    assert "--mode" not in help_text
    assert "--new-version" not in help_text


def test_git_branch_flag_removed():
    """[Unit] cli: git branch flag removed.

    Scenario:
        Focus on the `git branch flag removed` case for `cli` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `cli` branch for this case and the fixtures or monkeypatches that establish it.
    """
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--git-branch", "main"])

    assert exc_info.value.code == 2


def test_cli_uses_explicit_project_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Unit] cli: uses explicit project dir.

    Scenario:
        Focus on the `uses explicit project dir` case for `cli` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `cli` branch for this case and the fixtures or monkeypatches that establish it.
    """
    project_dir = tmp_path / "target-project"
    write_project(project_dir)
    captured: list[Path] = []

    monkeypatch.setattr(cli, "sanity_check", lambda config: None)
    monkeypatch.setattr(cli, "cleanup_old_wheels", lambda config: None)
    monkeypatch.setattr(cli, "build_wheel", lambda config: captured.append(config.project_dir))

    exit_code = cli.main(["--project-dir", str(project_dir)])

    assert exit_code == 0
    assert captured == [project_dir.resolve()]


def test_cli_default_run_cleans_and_builds_without_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Unit] cli: default run cleans and builds without pipeline.

    Scenario:
        Focus on the `default run cleans and builds without pipeline` case for `cli` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `cli` branch for this case and the fixtures or monkeypatches that establish it.
    """
    project_dir = tmp_path / "target-project"
    write_project(project_dir)
    calls: list[str] = []

    monkeypatch.setattr(cli, "sanity_check", lambda config: calls.append("sanity"))
    monkeypatch.setattr(cli, "cleanup_old_wheels", lambda config: calls.append("cleanup"))
    monkeypatch.setattr(cli, "build_wheel", lambda config: calls.append("build"))
    monkeypatch.setattr(
        cli,
        "run_release_pipeline",
        lambda steps, config=None: calls.append("pipeline"),
    )

    exit_code = cli.main(["--project-dir", str(project_dir), "--no-plugins"])

    assert exit_code == 0
    assert calls == ["sanity", "cleanup", "build"]


def test_cli_local_install_flag_adds_wheel_mode_local_install_step(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Unit] cli: local install flag adds wheel mode local install step.

    Scenario:
        Focus on the `local install flag adds wheel mode local install step` case for `cli` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `cli` branch for this case and the fixtures or monkeypatches that establish it.
    """
    project_dir = tmp_path / "target-project"
    write_project(project_dir)
    captured: list[list[ReleaseStep]] = []

    monkeypatch.setattr(cli, "sanity_check", lambda config: None)
    monkeypatch.setattr(cli, "cleanup_old_wheels", lambda config: None)
    monkeypatch.setattr(cli, "build_wheel", lambda config: None)
    monkeypatch.setattr(cli, "run_release_pipeline", lambda steps, config=None: captured.append(steps))

    exit_code = cli.main(["--project-dir", str(project_dir), "--no-plugins", "--local-install"])

    assert exit_code == 0
    assert len(captured) == 1
    assert [type(step) for step in captured[0]] == [LocalInstallStep]
    assert captured[0][0].dev_mode is False


def test_cli_local_dev_mode_implies_editable_local_install_and_prints_banner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    """[Unit] cli: local dev mode implies editable local install and prints banner.

    Scenario:
        Focus on the `local dev mode implies editable local install and prints banner` case for `cli` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `cli` branch for this case and the fixtures or monkeypatches that establish it.
    """
    project_dir = tmp_path / "target-project"
    write_project(project_dir)
    captured: list[list[ReleaseStep]] = []

    monkeypatch.setattr(cli, "sanity_check", lambda config: None)
    monkeypatch.setattr(cli, "cleanup_old_wheels", lambda config: None)
    monkeypatch.setattr(cli, "build_wheel", lambda config: None)
    monkeypatch.setattr(cli, "run_release_pipeline", lambda steps, config=None: captured.append(steps))

    exit_code = cli.main(["--project-dir", str(project_dir), "--no-plugins", "--local-dev-mode"])

    assert exit_code == 0
    assert [type(step) for step in captured[0]] == [LocalInstallStep]
    assert captured[0][0].dev_mode is True
    assert "development in progress" in capsys.readouterr().out


@pytest.mark.parametrize("removed", [["--mode", "build"], ["--new-version", "1.3.0"]])
def test_cli_rejects_removed_mode_flags(tmp_path: Path, removed: list[str]):
    """[Unit] cli: rejects removed mode flags.

    Scenario:
        Focus on the `rejects removed mode flags` case for `cli` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `cli` branch for this case and the fixtures or monkeypatches that establish it.
    """
    project_dir = tmp_path / "target-project"
    write_project(project_dir)

    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--project-dir", str(project_dir), *removed])

    assert exc_info.value.code == 2


@pytest.mark.parametrize(
    "flags",
    [
        ["--version", "--clean"],
        ["--version", "--set-version", "1.3.0"],
        ["--clean", "--set-version", "1.3.0"],
    ],
)
def test_cli_one_shot_flags_are_mutually_exclusive(tmp_path: Path, flags: list[str]):
    """[Unit] cli: one shot flags are mutually exclusive.

    Scenario:
        Focus on the `one shot flags are mutually exclusive` case for `cli` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `cli` branch for this case and the fixtures or monkeypatches that establish it.
    """
    project_dir = tmp_path / "target-project"
    write_project(project_dir)

    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--project-dir", str(project_dir), *flags])

    assert exc_info.value.code == 2


def test_cli_runs_release_pipeline_when_steps_selected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Unit] cli: runs release pipeline when steps selected.

    Scenario:
        Focus on the `runs release pipeline when steps selected` case for `cli` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `cli` branch for this case and the fixtures or monkeypatches that establish it.
    """
    project_dir = tmp_path / "target-project"
    write_project(project_dir)
    dist_dir = project_dir / "dist"
    dist_dir.mkdir()
    (dist_dir / "demo_package-1.2.3-py3-none-any.whl").write_text("wheel", encoding="utf-8")
    calls: list[list[str]] = []

    monkeypatch.setattr(cli, "sanity_check", lambda config: None)
    monkeypatch.setattr(cli, "cleanup_old_wheels", lambda config: None)
    monkeypatch.setattr(cli, "build_wheel", lambda config: None)
    monkeypatch.setattr(
        cli,
        "run_release_pipeline",
        lambda steps, config=None: calls.append([type(step).__name__ for step in steps]),
    )

    exit_code = cli.main(["--project-dir", str(project_dir), "--upload-s3"])

    assert exit_code == 0
    assert calls == [["UploadS3Step"]]


def test_cli_loads_configured_extra_steps_into_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Unit] cli: loads configured extra_steps into the release pipeline.

    Scenario:
        Focus on the `loads configured extra_steps into the release pipeline` case for `cli` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `cli` branch for this case and the fixtures or monkeypatches that establish it.
    """
    project_dir = tmp_path / "target-project"
    write_project(project_dir)
    (project_dir / "release_steps.py").write_text(
        """
from release_saga.steps.base import ReleaseStep


class ChangelogStep(ReleaseStep):
    name = "update changelog"

    def __init__(self, config):
        self.config = config

    def execute(self):
        pass

    def rollback(self):
        pass
""",
        encoding="utf-8",
    )
    (project_dir / "pyproject.toml").write_text(
        (project_dir / "pyproject.toml").read_text(encoding="utf-8")
        + '\n[tool.release-saga]\nextra_steps = ["release_steps.py:ChangelogStep"]\n',
        encoding="utf-8",
    )
    calls: list[list[str]] = []

    monkeypatch.setattr(cli, "sanity_check", lambda config: None)
    monkeypatch.setattr(cli, "cleanup_old_wheels", lambda config: None)
    monkeypatch.setattr(cli, "build_wheel", lambda config: None)
    monkeypatch.setattr(
        cli,
        "run_release_pipeline",
        lambda steps, config=None: calls.append([type(step).__name__ for step in steps]),
    )

    exit_code = cli.main(["--project-dir", str(project_dir)])

    assert exit_code == 0
    assert calls == [["ChangelogStep"]]


def test_cli_no_plugins_flag_skips_extra_steps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Unit] cli: --no-plugins flag skips extra_steps loading entirely.

    Scenario:
        Focus on the `--no-plugins flag skips extra_steps loading entirely` case for `cli` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `cli` branch for this case and the fixtures or monkeypatches that establish it.
    """
    project_dir = tmp_path / "target-project"
    write_project(project_dir)
    (project_dir / "pyproject.toml").write_text(
        (project_dir / "pyproject.toml").read_text(encoding="utf-8")
        + '\n[tool.release-saga]\nextra_steps = ["missing_module.py:MissingStep"]\n',
        encoding="utf-8",
    )
    calls: list[list[str]] = []

    monkeypatch.setattr(cli, "sanity_check", lambda config: None)
    monkeypatch.setattr(cli, "cleanup_old_wheels", lambda config: None)
    monkeypatch.setattr(cli, "build_wheel", lambda config: None)
    monkeypatch.setattr(
        cli,
        "run_release_pipeline",
        lambda steps, config=None: calls.append([type(step).__name__ for step in steps]),
    )

    exit_code = cli.main(["--project-dir", str(project_dir), "--no-plugins"])

    assert exit_code == 0
    assert calls == []


def test_cli_plugin_load_error_exits_with_usage_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    """[Unit] cli: a broken extra_steps entry causes a clean argument-error exit.

    Scenario:
        Focus on the `a broken extra_steps entry causes a clean argument-error exit` case for `cli` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `cli` branch for this case and the fixtures or monkeypatches that establish it.
    """
    project_dir = tmp_path / "target-project"
    write_project(project_dir)
    (project_dir / "pyproject.toml").write_text(
        (project_dir / "pyproject.toml").read_text(encoding="utf-8")
        + '\n[tool.release-saga]\nextra_steps = ["missing_module.py:MissingStep"]\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(cli, "sanity_check", lambda config: None)
    monkeypatch.setattr(cli, "cleanup_old_wheels", lambda config: None)
    monkeypatch.setattr(cli, "build_wheel", lambda config: None)

    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--project-dir", str(project_dir)])

    assert exc_info.value.code == 2
    assert "Plugin file not found" in capsys.readouterr().err


def test_cli_version_flag_prints_target_project_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    """[Unit] cli: version flag prints target project version.

    Scenario:
        Focus on the `version flag prints target project version` case for `cli` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `cli` branch for this case and the fixtures or monkeypatches that establish it.
    """
    project_dir = tmp_path / "target-project"
    write_project(project_dir)

    exit_code = cli.main(["--project-dir", str(project_dir), "--version"])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "1.2.3"


def test_cli_version_flag_skips_build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Unit] cli: version flag skips build.

    Scenario:
        Focus on the `version flag skips build` case for `cli` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `cli` branch for this case and the fixtures or monkeypatches that establish it.
    """
    project_dir = tmp_path / "target-project"
    write_project(project_dir)

    monkeypatch.setattr(cli, "sanity_check", lambda config: (_ for _ in ()).throw(AssertionError("should not run")))

    exit_code = cli.main(["--project-dir", str(project_dir), "--version", "--local-install"])

    assert exit_code == 0


def test_cli_set_version_requires_value(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Unit] cli: set version requires value.

    Scenario:
        Focus on the `set version requires value` case for `cli` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `cli` branch for this case and the fixtures or monkeypatches that establish it.
    """
    project_dir = tmp_path / "target-project"
    write_project(project_dir)

    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--project-dir", str(project_dir), "--set-version"])

    assert exc_info.value.code == 2


def test_cli_set_version_calls_set_release_version_and_skips_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Unit] cli: set version calls set release version and skips pipeline.

    Scenario:
        Focus on the `set version calls set release version and skips pipeline` case for `cli` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `cli` branch for this case and the fixtures or monkeypatches that establish it.
    """
    project_dir = tmp_path / "target-project"
    write_project(project_dir)
    calls: list[tuple[str, str]] = []

    monkeypatch.setattr(cli, "sanity_check", lambda config: (_ for _ in ()).throw(AssertionError("should not run")))
    monkeypatch.setattr(
        cli,
        "set_release_version",
        lambda config, new_version: calls.append((config.version, new_version)),
    )
    monkeypatch.setattr(
        cli,
        "run_release_pipeline",
        lambda steps: (_ for _ in ()).throw(AssertionError("should not run")),
    )

    exit_code = cli.main(
        [
            "--project-dir",
            str(project_dir),
            "--set-version",
            "1.3.0",
            "--create-release",
        ]
    )

    assert exit_code == 0
    assert calls == [("1.2.3", "1.3.0")]


def test_cli_clean_flag_recovers_latest_incomplete_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Unit] cli: clean flag reconstructs the latest interrupted release run."""
    project_dir = tmp_path / "target-project"
    write_project(project_dir)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    config = cli.load_config(project_dir.resolve(), {})
    history = cli.RunHistory.create(config, [cli.GitTagStep(config)])
    history.set_step_status(0, "completed")
    captured: list[str] = []

    monkeypatch.setattr(
        cli,
        "clean_release_run",
        lambda steps, run: captured.extend([type(steps[0]).__name__, run.data["run_id"]]),
    )
    monkeypatch.setattr(
        cli,
        "sanity_check",
        lambda config: (_ for _ in ()).throw(AssertionError("should not run")),
    )

    exit_code = cli.main(["--clean", "--project-dir", str(project_dir)])

    assert exit_code == 0
    assert captured == ["GitTagStep", history.data["run_id"]]


def test_cli_clean_flag_recovers_in_progress_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Unit] cli: clean flag reconstructs uncertain in-progress steps."""
    project_dir = tmp_path / "target-project"
    write_project(project_dir)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    config = cli.load_config(project_dir.resolve(), {})
    history = cli.RunHistory.create(config, [cli.GitTagStep(config)])
    history.set_step_status(0, "in_progress")
    captured: list[str] = []

    monkeypatch.setattr(
        cli,
        "clean_release_run",
        lambda steps, run: captured.extend([type(steps[0]).__name__, run.data["run_id"]]),
    )
    monkeypatch.setattr(
        cli,
        "sanity_check",
        lambda config: (_ for _ in ()).throw(AssertionError("should not run")),
    )

    exit_code = cli.main(["--clean", "--project-dir", str(project_dir)])

    assert exit_code == 0
    assert captured == ["GitTagStep", history.data["run_id"]]


def test_cli_clean_flag_reconstructs_local_install_step_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Unit] cli: clean flag rebuilds a recorded local install step in its recorded mode."""
    project_dir = tmp_path / "target-project"
    write_project(project_dir)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    config = cli.load_config(project_dir.resolve(), {})
    history = cli.RunHistory.create(config, [LocalInstallStep(config, dev_mode=True)])
    history.set_step_status(0, "completed", {"dev_mode": True})
    captured: list[ReleaseStep] = []

    monkeypatch.setattr(cli, "clean_release_run", lambda steps, run: captured.extend(steps))

    exit_code = cli.main(["--clean", "--project-dir", str(project_dir)])

    assert exit_code == 0
    assert [type(step) for step in captured] == [LocalInstallStep]
    assert captured[0].dev_mode is True


class _RecordedPluginStep(ReleaseStep):
    name = "recorded plugin step"

    def execute(self):
        pass

    def rollback(self):
        pass


def _record_completed_run(project_dir: Path, steps_factory) -> None:
    config = cli.load_config(project_dir.resolve(), {})
    steps = steps_factory(config)
    history = cli.RunHistory.create(config, steps)
    for index, step in enumerate(steps):
        history.set_step_status(index, "completed", step.recovery_data())


def test_cli_clean_flag_reconstructs_every_built_in_step(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Unit] cli: clean flag rebuilds every built-in step type from recorded history."""
    project_dir = tmp_path / "target-project"
    write_project(project_dir)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    _record_completed_run(
        project_dir,
        lambda config: [
            LocalInstallStep(config),
            cli.UploadS3Step(config, Path("demo_package-1.2.3-py3-none-any.whl")),
            cli.GitTagStep(config),
            cli.GitHubReleaseStep(config),
            cli.PublishPyPiStep(config),
        ],
    )
    monkeypatch.setattr(
        cli,
        "load_plugin_steps",
        lambda config: (_ for _ in ()).throw(AssertionError("should not load plugins")),
    )
    captured: list[ReleaseStep] = []
    monkeypatch.setattr(cli, "clean_release_run", lambda steps, run: captured.extend(steps))

    exit_code = cli.main(["--clean", "--project-dir", str(project_dir)])

    assert exit_code == 0
    assert [type(step).__name__ for step in captured] == [
        "LocalInstallStep",
        "UploadS3Step",
        "GitTagStep",
        "GitHubReleaseStep",
        "PublishPyPiStep",
    ]
    assert captured[1].wheel_path == Path("demo_package-1.2.3-py3-none-any.whl")


def test_cli_clean_flag_reconstructs_recorded_plugin_step(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Unit] cli: clean flag matches a recorded plugin step against freshly loaded plugins."""
    project_dir = tmp_path / "target-project"
    write_project(project_dir)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    _record_completed_run(project_dir, lambda config: [_RecordedPluginStep()])
    plugin = _RecordedPluginStep()
    monkeypatch.setattr(cli, "load_plugin_steps", lambda config: [plugin])
    captured: list[ReleaseStep] = []
    monkeypatch.setattr(cli, "clean_release_run", lambda steps, run: captured.extend(steps))

    exit_code = cli.main(["--clean", "--project-dir", str(project_dir)])

    assert exit_code == 0
    assert captured == [plugin]


def test_cli_clean_flag_errors_when_recorded_step_cannot_be_reconstructed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    """[Unit] cli: clean flag exits with a usage error for an unknown recorded step."""
    project_dir = tmp_path / "target-project"
    write_project(project_dir)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    _record_completed_run(project_dir, lambda config: [_RecordedPluginStep()])
    monkeypatch.setattr(cli, "load_plugin_steps", lambda config: [])

    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--clean", "--project-dir", str(project_dir)])

    assert exc_info.value.code == 2
    assert "Cannot reconstruct recorded release step 'recorded plugin step'" in capsys.readouterr().err


def test_cli_clean_flag_reports_plugin_load_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    """[Unit] cli: clean flag exits with a usage error when plugins fail to load."""
    project_dir = tmp_path / "target-project"
    write_project(project_dir)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    _record_completed_run(project_dir, lambda config: [_RecordedPluginStep()])

    def broken_plugins(config):
        raise cli.PluginLoadError("broken plugin")

    monkeypatch.setattr(cli, "load_plugin_steps", broken_plugins)

    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--clean", "--project-dir", str(project_dir)])

    assert exc_info.value.code == 2
    assert "broken plugin" in capsys.readouterr().err


def test_cli_clean_flag_reports_when_no_run_needs_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    """[Unit] cli: clean flag is a no-op when no interrupted run exists."""
    project_dir = tmp_path / "target-project"
    write_project(project_dir)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))

    exit_code = cli.main(["--clean", "--project-dir", str(project_dir)])

    assert exit_code == 0
    assert "No incomplete release run found" in capsys.readouterr().out


def test_dunder_main_module_exits_cleanly_on_help(monkeypatch: pytest.MonkeyPatch):
    """[Integration] __main__: help exits cleanly.

    Scenario:
        Focus on the `help exits cleanly` case for `__main__` and assert the expected outcome.

    Boundaries:
        Covers the local integration path between adjacent components while avoiding real external service calls.

    On failure, first check:
        The `__main__` branch for this case and the fixtures or monkeypatches that establish it.
    """
    monkeypatch.setattr(sys, "argv", ["release-saga", "--help"])

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("release_saga.__main__", run_name="__main__")

    assert exc_info.value.code == 0
