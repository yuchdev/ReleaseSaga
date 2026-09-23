import runpy
import sys
from pathlib import Path

import pytest

from release_saga import cli


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
    assert "--new-version" in help_text


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
    monkeypatch.setattr(cli, "build_wheel", lambda config: captured.append(config.project_dir))

    exit_code = cli.main(["--mode", "build", "--project-dir", str(project_dir)])

    assert exit_code == 0
    assert captured == [project_dir.resolve()]


def test_cli_install_mode_cleans_builds_and_installs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Unit] cli: install mode cleans builds and installs.

    Scenario:
        Focus on the `install mode cleans builds and installs` case for `cli` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `cli` branch for this case and the fixtures or monkeypatches that establish it.
    """
    project_dir = tmp_path / "target-project"
    write_project(project_dir)
    calls: list[str] = []

    monkeypatch.setattr(cli, "sanity_check", lambda config: None)
    monkeypatch.setattr(cli, "cleanup_old_wheels", lambda config: calls.append("cleanup"))
    monkeypatch.setattr(cli, "build_wheel", lambda config: calls.append("build"))
    monkeypatch.setattr(cli, "install_wheel", lambda config: calls.append("install"))

    exit_code = cli.main(["--mode", "install", "--project-dir", str(project_dir)])

    assert exit_code == 0
    assert calls == ["cleanup", "build", "install"]


def test_cli_dev_mode_installs_editable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Unit] cli: dev mode installs editable.

    Scenario:
        Focus on the `dev mode installs editable` case for `cli` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `cli` branch for this case and the fixtures or monkeypatches that establish it.
    """
    project_dir = tmp_path / "target-project"
    write_project(project_dir)
    calls: list[str] = []

    monkeypatch.setattr(cli, "sanity_check", lambda config: None)
    monkeypatch.setattr(cli, "cleanup_old_wheels", lambda config: calls.append("cleanup"))
    monkeypatch.setattr(cli, "build_wheel", lambda config: calls.append("build"))
    monkeypatch.setattr(cli, "install_wheel_devmode", lambda config: calls.append("dev"))

    exit_code = cli.main(["--mode", "dev", "--project-dir", str(project_dir)])

    assert exit_code == 0
    assert calls == ["cleanup", "build", "dev"]


def test_cli_reinstall_mode_is_default_and_runs_full_cycle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Unit] cli: reinstall mode is default and runs full cycle.

    Scenario:
        Focus on the `reinstall mode is default and runs full cycle` case for `cli` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `cli` branch for this case and the fixtures or monkeypatches that establish it.
    """
    project_dir = tmp_path / "target-project"
    write_project(project_dir)
    calls: list[str] = []

    monkeypatch.setattr(cli, "sanity_check", lambda config: None)
    monkeypatch.setattr(cli, "cleanup_old_wheels", lambda config: calls.append("cleanup"))
    monkeypatch.setattr(cli, "uninstall_wheel", lambda config: calls.append("uninstall"))
    monkeypatch.setattr(cli, "build_wheel", lambda config: calls.append("build"))
    monkeypatch.setattr(cli, "install_wheel", lambda config: calls.append("install"))

    exit_code = cli.main(["--project-dir", str(project_dir)])

    assert exit_code == 0
    assert calls == ["cleanup", "uninstall", "build", "install"]


def test_cli_uninstall_mode_skips_release_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Unit] cli: uninstall mode skips release pipeline.

    Scenario:
        Focus on the `uninstall mode skips release pipeline` case for `cli` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `cli` branch for this case and the fixtures or monkeypatches that establish it.
    """
    project_dir = tmp_path / "target-project"
    write_project(project_dir)
    calls: list[str] = []

    monkeypatch.setattr(cli, "sanity_check", lambda config: None)
    monkeypatch.setattr(cli, "uninstall_wheel", lambda config: calls.append("uninstall"))
    monkeypatch.setattr(cli, "run_release_pipeline", lambda steps: calls.append("pipeline"))

    exit_code = cli.main(["--mode", "uninstall", "--project-dir", str(project_dir), "--create-release"])

    assert exit_code == 0
    assert calls == ["uninstall"]


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
    monkeypatch.setattr(cli, "build_wheel", lambda config: None)
    monkeypatch.setattr(
        cli,
        "run_release_pipeline",
        lambda steps, config=None: calls.append([type(step).__name__ for step in steps]),
    )

    exit_code = cli.main(["--mode", "build", "--project-dir", str(project_dir), "--upload-s3"])

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
    monkeypatch.setattr(cli, "build_wheel", lambda config: None)
    monkeypatch.setattr(
        cli,
        "run_release_pipeline",
        lambda steps, config=None: calls.append([type(step).__name__ for step in steps]),
    )

    exit_code = cli.main(["--mode", "build", "--project-dir", str(project_dir)])

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
    monkeypatch.setattr(cli, "build_wheel", lambda config: None)
    monkeypatch.setattr(
        cli,
        "run_release_pipeline",
        lambda steps, config=None: calls.append([type(step).__name__ for step in steps]),
    )

    exit_code = cli.main(["--mode", "build", "--project-dir", str(project_dir), "--no-plugins"])

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
    monkeypatch.setattr(cli, "build_wheel", lambda config: None)

    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--mode", "build", "--project-dir", str(project_dir)])

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


def test_cli_version_flag_skips_mode_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Unit] cli: version flag skips mode dispatch.

    Scenario:
        Focus on the `version flag skips mode dispatch` case for `cli` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `cli` branch for this case and the fixtures or monkeypatches that establish it.
    """
    project_dir = tmp_path / "target-project"
    write_project(project_dir)

    monkeypatch.setattr(cli, "sanity_check", lambda config: (_ for _ in ()).throw(AssertionError("should not run")))

    exit_code = cli.main(["--project-dir", str(project_dir), "--version", "--mode", "build"])

    assert exit_code == 0


def test_cli_set_version_mode_requires_new_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Unit] cli: set version mode requires new version.

    Scenario:
        Focus on the `set version mode requires new version` case for `cli` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `cli` branch for this case and the fixtures or monkeypatches that establish it.
    """
    project_dir = tmp_path / "target-project"
    write_project(project_dir)

    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--project-dir", str(project_dir), "--mode", "set-version"])

    assert exc_info.value.code == 2


def test_cli_set_version_mode_calls_set_release_version_and_skips_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Unit] cli: set version mode calls set release version and skips pipeline.

    Scenario:
        Focus on the `set version mode calls set release version and skips pipeline` case for `cli` and assert the expected outcome.

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
            "--mode",
            "set-version",
            "--new-version",
            "1.3.0",
            "--create-release",
        ]
    )

    assert exit_code == 0
    assert calls == [("1.2.3", "1.3.0")]


def test_cli_clean_mode_recovers_latest_incomplete_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Unit] cli: clean mode reconstructs the latest interrupted release run."""
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

    exit_code = cli.main(["--mode", "clean", "--project-dir", str(project_dir)])

    assert exit_code == 0
    assert captured == ["GitTagStep", history.data["run_id"]]


def test_cli_clean_mode_recovers_in_progress_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Unit] cli: clean mode reconstructs uncertain in-progress steps."""
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

    exit_code = cli.main(["--mode", "clean", "--project-dir", str(project_dir)])

    assert exit_code == 0
    assert captured == ["GitTagStep", history.data["run_id"]]


def test_cli_clean_mode_reports_when_no_run_needs_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    """[Unit] cli: clean mode is a no-op when no interrupted run exists."""
    project_dir = tmp_path / "target-project"
    write_project(project_dir)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))

    exit_code = cli.main(["--mode", "clean", "--project-dir", str(project_dir)])

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
