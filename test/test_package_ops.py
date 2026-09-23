import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from release_saga.config import ReleaseConfig
from release_saga.package_ops import (
    PIP,
    PYTHON,
    build_wheel,
    cleanup_old_wheels,
    command_ok,
    ensure_pip,
    executable_exists,
    install_wheel,
    install_wheel_devmode,
    resolve_wheel_path,
    sanity_check,
    uninstall_wheel,
)


def make_config(project_dir: Path) -> ReleaseConfig:
    return ReleaseConfig(
        project_dir=project_dir,
        package_name="demo_package",
        package_name_dash="demo-package",
        version="1.2.3",
    )


@pytest.fixture(autouse=True)
def _no_pip_bootstrap(monkeypatch: pytest.MonkeyPatch):
    """Keep pip-using helpers from probing or bootstrapping the real interpreter."""
    monkeypatch.setattr("release_saga.package_ops.ensure_pip", lambda: None)


def test_ensure_pip_skips_bootstrap_when_pip_is_available(monkeypatch: pytest.MonkeyPatch):
    """[Local] ensure_pip: skips ensurepip when pip is already importable.

    Scenario:
        `python -m pip --version` succeeds, so no bootstrap command may run.

    Boundaries:
        Covers patched subprocess calls without touching the real interpreter.

    On failure, first check:
        The `command_ok` probe in `ensure_pip`.
    """
    commands: list[list[str]] = []
    monkeypatch.setattr("release_saga.package_ops.command_ok", lambda cmd, cwd=None: True)
    monkeypatch.setattr("release_saga.package_ops.run", lambda cmd, **kwargs: commands.append(cmd))

    ensure_pip()

    assert commands == []


def test_ensure_pip_bootstraps_pip_when_missing(monkeypatch: pytest.MonkeyPatch):
    """[Local] ensure_pip: runs ensurepip when pip is missing (uv-created venv).

    Scenario:
        `python -m pip --version` fails, as in a `uv venv`, so `ensurepip` must install pip.

    Boundaries:
        Covers patched subprocess calls without touching the real interpreter.

    On failure, first check:
        The `ensurepip` command built in `ensure_pip`.
    """
    commands: list[list[str]] = []
    monkeypatch.setattr("release_saga.package_ops.command_ok", lambda cmd, cwd=None: False)
    monkeypatch.setattr("release_saga.package_ops.run", lambda cmd, **kwargs: commands.append(cmd))

    ensure_pip()

    assert commands == [[PYTHON, "-m", "ensurepip", "--upgrade"]]


def test_resolve_wheel_path_matches_prefix_not_exact_suffix(tmp_path: Path):
    """[Local] resolve_wheel_path: matches prefix not exact suffix.

    Scenario:
        Focus on the `matches prefix not exact suffix` case for `resolve_wheel_path` and assert the expected outcome.

    Boundaries:
        Covers temporary local files, directories, or subprocess arguments without performing a real release.

    On failure, first check:
        The `resolve_wheel_path` branch for this case and the fixtures or monkeypatches that establish it.
    """
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    matching = dist_dir / "demo_package-1.2.3-py3-none-any.whl"
    misleading_newer = dist_dir / "demo_package-1.2.30-py3-none-any.whl"
    matching.write_text("old", encoding="utf-8")
    misleading_newer.write_text("new", encoding="utf-8")
    os.utime(matching, (1, 1))
    os.utime(misleading_newer, (2, 2))

    wheel_path = resolve_wheel_path(make_config(tmp_path))

    assert wheel_path == matching


def test_resolve_wheel_path_raises_when_no_match(tmp_path: Path):
    """[Local] resolve_wheel_path: raises when no match.

    Scenario:
        Focus on the `raises when no match` case for `resolve_wheel_path` and assert the expected outcome.

    Boundaries:
        Covers temporary local files, directories, or subprocess arguments without performing a real release.

    On failure, first check:
        The `resolve_wheel_path` branch for this case and the fixtures or monkeypatches that establish it.
    """
    (tmp_path / "dist").mkdir()

    with pytest.raises(FileNotFoundError):
        resolve_wheel_path(make_config(tmp_path))


def test_cleanup_old_wheels_only_removes_matching_package_files(tmp_path: Path):
    """[Local] cleanup_old_wheels: only removes matching package files.

    Scenario:
        Focus on the `only removes matching package files` case for `cleanup_old_wheels` and assert the expected outcome.

    Boundaries:
        Covers temporary local files, directories, or subprocess arguments without performing a real release.

    On failure, first check:
        The `cleanup_old_wheels` branch for this case and the fixtures or monkeypatches that establish it.
    """
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    matching = dist_dir / "demo_package-1.2.3-py3-none-any.whl"
    matching_sdist = dist_dir / "demo_package-1.2.3.tar.gz"
    other = dist_dir / "other_package-1.2.3-py3-none-any.whl"
    matching.write_text("x", encoding="utf-8")
    matching_sdist.write_text("z", encoding="utf-8")
    other.write_text("y", encoding="utf-8")

    cleanup_old_wheels(make_config(tmp_path))

    assert not matching.exists()
    assert matching_sdist.exists()
    assert other.exists()


def test_cleanup_old_wheels_no_op_when_dist_dir_missing(tmp_path: Path):
    """[Local] cleanup_old_wheels: no op when dist dir missing.

    Scenario:
        Focus on the `no op when dist dir missing` case for `cleanup_old_wheels` and assert the expected outcome.

    Boundaries:
        Covers temporary local files, directories, or subprocess arguments without performing a real release.

    On failure, first check:
        The `cleanup_old_wheels` branch for this case and the fixtures or monkeypatches that establish it.
    """
    cleanup_old_wheels(make_config(tmp_path))


def test_executable_exists_true_when_command_succeeds(monkeypatch: pytest.MonkeyPatch):
    """[Local] executable_exists: true when command succeeds.

    Scenario:
        Focus on the `true when command succeeds` case for `executable_exists` and assert the expected outcome.

    Boundaries:
        Covers temporary local files, directories, or subprocess arguments without performing a real release.

    On failure, first check:
        The `executable_exists` branch for this case and the fixtures or monkeypatches that establish it.
    """
    monkeypatch.setattr(
        "release_saga.package_ops.run",
        lambda cmd, **kwargs: SimpleNamespace(returncode=0),
    )

    assert executable_exists("git") is True


def test_executable_exists_false_when_command_fails(monkeypatch: pytest.MonkeyPatch):
    """[Local] executable_exists: false when command fails.

    Scenario:
        Focus on the `false when command fails` case for `executable_exists` and assert the expected outcome.

    Boundaries:
        Covers temporary local files, directories, or subprocess arguments without performing a real release.

    On failure, first check:
        The `executable_exists` branch for this case and the fixtures or monkeypatches that establish it.
    """
    monkeypatch.setattr(
        "release_saga.package_ops.run",
        lambda cmd, **kwargs: SimpleNamespace(returncode=1),
    )

    assert executable_exists("git") is False


def test_executable_exists_false_when_not_found(monkeypatch: pytest.MonkeyPatch):
    """[Local] executable_exists: false when not found.

    Scenario:
        Focus on the `false when not found` case for `executable_exists` and assert the expected outcome.

    Boundaries:
        Covers temporary local files, directories, or subprocess arguments without performing a real release.

    On failure, first check:
        The `executable_exists` branch for this case and the fixtures or monkeypatches that establish it.
    """
    def raise_not_found(cmd, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr("release_saga.package_ops.run", raise_not_found)

    assert executable_exists("nonexistent-tool") is False


def test_command_ok_true_when_command_succeeds(monkeypatch: pytest.MonkeyPatch):
    """[Local] command_ok: true when command succeeds.

    Scenario:
        Focus on the `true when command succeeds` case for `command_ok` and assert the expected outcome.

    Boundaries:
        Covers temporary local files, directories, or subprocess arguments without performing a real release.

    On failure, first check:
        The `command_ok` branch for this case and the fixtures or monkeypatches that establish it.
    """
    monkeypatch.setattr(
        "release_saga.package_ops.run",
        lambda cmd, **kwargs: SimpleNamespace(returncode=0),
    )

    assert command_ok(["git", "status"]) is True


def test_command_ok_false_when_not_found(monkeypatch: pytest.MonkeyPatch):
    """[Local] command_ok: false when not found.

    Scenario:
        Focus on the `false when not found` case for `command_ok` and assert the expected outcome.

    Boundaries:
        Covers temporary local files, directories, or subprocess arguments without performing a real release.

    On failure, first check:
        The `command_ok` branch for this case and the fixtures or monkeypatches that establish it.
    """
    def raise_not_found(cmd, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr("release_saga.package_ops.run", raise_not_found)

    assert command_ok(["nonexistent-tool"]) is False


def test_sanity_check_passes_when_src_layout_exists(tmp_path: Path):
    """[Local] sanity_check: passes when src layout exists.

    Scenario:
        Focus on the `passes when src layout exists` case for `sanity_check` and assert the expected outcome.

    Boundaries:
        Covers temporary local files, directories, or subprocess arguments without performing a real release.

    On failure, first check:
        The `sanity_check` branch for this case and the fixtures or monkeypatches that establish it.
    """
    (tmp_path / "src" / "demo_package").mkdir(parents=True)

    sanity_check(make_config(tmp_path))


def test_sanity_check_exits_when_src_layout_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    """[Local] sanity_check: exits when src layout missing.

    Scenario:
        Focus on the `exits when src layout missing` case for `sanity_check` and assert the expected outcome.

    Boundaries:
        Covers temporary local files, directories, or subprocess arguments without performing a real release.

    On failure, first check:
        The `sanity_check` branch for this case and the fixtures or monkeypatches that establish it.
    """
    with pytest.raises(SystemExit) as exc_info:
        sanity_check(make_config(tmp_path))

    assert exc_info.value.code == 1
    assert "Cannot find src/demo_package" in capsys.readouterr().out


def test_uninstall_wheel_runs_pip_uninstall(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """[Local] uninstall_wheel: runs pip uninstall.

    Scenario:
        Focus on the `runs pip uninstall` case for `uninstall_wheel` and assert the expected outcome.

    Boundaries:
        Covers temporary local files, directories, or subprocess arguments without performing a real release.

    On failure, first check:
        The `uninstall_wheel` branch for this case and the fixtures or monkeypatches that establish it.
    """
    commands: list[list[str]] = []
    monkeypatch.setattr(
        "release_saga.package_ops.run",
        lambda cmd, **kwargs: commands.append(cmd),
    )

    uninstall_wheel(make_config(tmp_path))

    assert commands == [[*PIP, "uninstall", "-y", "demo-package"]]


def test_build_wheel_upgrades_pip_and_build_then_builds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Local] build_wheel: upgrades pip and build then builds.

    Scenario:
        Focus on the `upgrades pip and build then builds` case for `build_wheel` and assert the expected outcome.

    Boundaries:
        Covers temporary local files, directories, or subprocess arguments without performing a real release.

    On failure, first check:
        The `build_wheel` branch for this case and the fixtures or monkeypatches that establish it.
    """
    commands: list[list[str]] = []
    monkeypatch.setattr(
        "release_saga.package_ops.run",
        lambda cmd, **kwargs: commands.append(cmd),
    )

    build_wheel(make_config(tmp_path))

    assert commands == [
        [*PIP, "install", "--upgrade", "pip"],
        [*PIP, "install", "--upgrade", "build"],
        [PYTHON, "-m", "build"],
    ]


def test_install_wheel_installs_resolved_wheel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """[Local] install_wheel: installs resolved wheel.

    Scenario:
        Focus on the `installs resolved wheel` case for `install_wheel` and assert the expected outcome.

    Boundaries:
        Covers temporary local files, directories, or subprocess arguments without performing a real release.

    On failure, first check:
        The `install_wheel` branch for this case and the fixtures or monkeypatches that establish it.
    """
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    wheel = dist_dir / "demo_package-1.2.3-py3-none-any.whl"
    wheel.write_text("wheel", encoding="utf-8")
    commands: list[list[str]] = []
    monkeypatch.setattr(
        "release_saga.package_ops.run",
        lambda cmd, **kwargs: commands.append(cmd),
    )

    install_wheel(make_config(tmp_path))

    assert commands == [[*PIP, "install", str(wheel)]]


def test_install_wheel_devmode_runs_editable_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """[Local] install_wheel_devmode: runs editable install.

    Scenario:
        Focus on the `runs editable install` case for `install_wheel_devmode` and assert the expected outcome.

    Boundaries:
        Covers temporary local files, directories, or subprocess arguments without performing a real release.

    On failure, first check:
        The `install_wheel_devmode` branch for this case and the fixtures or monkeypatches that establish it.
    """
    commands: list[list[str]] = []
    monkeypatch.setattr(
        "release_saga.package_ops.run",
        lambda cmd, **kwargs: commands.append(cmd),
    )

    install_wheel_devmode(make_config(tmp_path))

    assert commands == [[*PIP, "install", "-e", "."]]
