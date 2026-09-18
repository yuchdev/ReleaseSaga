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
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--git-branch", "main"])

    assert exc_info.value.code == 2


def test_cli_uses_explicit_project_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
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
        lambda steps: calls.append([type(step).__name__ for step in steps]),
    )

    exit_code = cli.main(["--mode", "build", "--project-dir", str(project_dir), "--upload-s3"])

    assert exit_code == 0
    assert calls == [["UploadS3Step"]]


def test_cli_version_flag_prints_target_project_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    project_dir = tmp_path / "target-project"
    write_project(project_dir)

    exit_code = cli.main(["--project-dir", str(project_dir), "--version"])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "1.2.3"


def test_cli_version_flag_skips_mode_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    project_dir = tmp_path / "target-project"
    write_project(project_dir)

    monkeypatch.setattr(cli, "sanity_check", lambda config: (_ for _ in ()).throw(AssertionError("should not run")))

    exit_code = cli.main(["--project-dir", str(project_dir), "--version", "--mode", "build"])

    assert exit_code == 0


def test_cli_set_version_mode_requires_new_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    project_dir = tmp_path / "target-project"
    write_project(project_dir)

    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--project-dir", str(project_dir), "--mode", "set-version"])

    assert exc_info.value.code == 2


def test_cli_set_version_mode_calls_set_release_version_and_skips_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
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


def test_dunder_main_module_exits_cleanly_on_help(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sys, "argv", ["release-saga", "--help"])

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("release_saga.__main__", run_name="__main__")

    assert exc_info.value.code == 0
