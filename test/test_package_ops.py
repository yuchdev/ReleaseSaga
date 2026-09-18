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


def test_resolve_wheel_path_matches_prefix_not_exact_suffix(tmp_path: Path) -> None:
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


def test_resolve_wheel_path_raises_when_no_match(tmp_path: Path) -> None:
    (tmp_path / "dist").mkdir()

    with pytest.raises(FileNotFoundError):
        resolve_wheel_path(make_config(tmp_path))


def test_cleanup_old_wheels_only_removes_matching_package_files(tmp_path: Path) -> None:
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


def test_cleanup_old_wheels_no_op_when_dist_dir_missing(tmp_path: Path) -> None:
    cleanup_old_wheels(make_config(tmp_path))


def test_executable_exists_true_when_command_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "release_saga.package_ops.run",
        lambda cmd, **kwargs: SimpleNamespace(returncode=0),
    )

    assert executable_exists("git") is True


def test_executable_exists_false_when_command_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "release_saga.package_ops.run",
        lambda cmd, **kwargs: SimpleNamespace(returncode=1),
    )

    assert executable_exists("git") is False


def test_executable_exists_false_when_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_not_found(cmd, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr("release_saga.package_ops.run", raise_not_found)

    assert executable_exists("nonexistent-tool") is False


def test_command_ok_true_when_command_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "release_saga.package_ops.run",
        lambda cmd, **kwargs: SimpleNamespace(returncode=0),
    )

    assert command_ok(["git", "status"]) is True


def test_command_ok_false_when_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_not_found(cmd, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr("release_saga.package_ops.run", raise_not_found)

    assert command_ok(["nonexistent-tool"]) is False


def test_sanity_check_passes_when_src_layout_exists(tmp_path: Path) -> None:
    (tmp_path / "src" / "demo_package").mkdir(parents=True)

    sanity_check(make_config(tmp_path))


def test_sanity_check_exits_when_src_layout_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        sanity_check(make_config(tmp_path))

    assert exc_info.value.code == 1
    assert "Cannot find src/demo_package" in capsys.readouterr().out


def test_uninstall_wheel_runs_pip_uninstall(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
) -> None:
    commands: list[list[str]] = []
    monkeypatch.setattr(
        "release_saga.package_ops.run",
        lambda cmd, **kwargs: commands.append(cmd),
    )

    build_wheel(make_config(tmp_path))

    assert commands == [
        [PYTHON, "-m", "pip", "install", "--upgrade", "pip"],
        [PYTHON, "-m", "pip", "install", "--upgrade", "build"],
        [PYTHON, "-m", "build"],
    ]


def test_install_wheel_installs_resolved_wheel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
) -> None:
    commands: list[list[str]] = []
    monkeypatch.setattr(
        "release_saga.package_ops.run",
        lambda cmd, **kwargs: commands.append(cmd),
    )

    install_wheel_devmode(make_config(tmp_path))

    assert commands == [[*PIP, "install", "-e", "."]]
