import os
from pathlib import Path

from release_saga.config import ReleaseConfig
from release_saga.package_ops import cleanup_old_wheels, resolve_wheel_path


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
    older = dist_dir / "demo_package-1.2.3-py3-none-any.whl"
    newer = dist_dir / "demo_package-1.2.3-cp311-cp311-manylinux.whl"
    older.write_text("old", encoding="utf-8")
    newer.write_text("new", encoding="utf-8")
    os.utime(older, (1, 1))
    os.utime(newer, (2, 2))

    wheel_path = resolve_wheel_path(make_config(tmp_path))

    assert wheel_path == newer


def test_cleanup_old_wheels_only_removes_matching_package_files(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    matching = dist_dir / "demo_package-1.2.3-py3-none-any.whl"
    other = dist_dir / "other_package-1.2.3-py3-none-any.whl"
    matching.write_text("x", encoding="utf-8")
    other.write_text("y", encoding="utf-8")

    cleanup_old_wheels(make_config(tmp_path))

    assert not matching.exists()
    assert other.exists()
