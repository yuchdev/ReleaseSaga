from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path
from subprocess import run

from .config import ReleaseConfig

PYTHON = sys.executable
PIP = [PYTHON, "-m", "pip"]


def executable_exists(executable: str) -> bool:
    """Return True when the named executable is available."""
    try:
        return run([executable, "--version"], capture_output=True).returncode == 0
    except FileNotFoundError:
        return False


def command_ok(cmd: Sequence[str], cwd: Path | None = None) -> bool:
    """Return True when the command exists and exits successfully."""
    try:
        return run(list(cmd), capture_output=True, cwd=cwd).returncode == 0
    except FileNotFoundError:
        return False


def sanity_check(config: ReleaseConfig) -> None:
    """Validate the expected source layout for the target project."""
    source_dir = config.project_dir / "src" / config.package_name
    if not source_dir.is_dir():
        print(f"Cannot find src/{config.package_name}")
        raise SystemExit(1)


def resolve_wheel_path(config: ReleaseConfig) -> Path:
    """Resolve the newest matching wheel for the configured package version."""
    dist_dir = config.project_dir / "dist"
    candidates = sorted(
        (path for path in config.project_dir.glob(config.wheel_glob) if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    prefix = f"{config.package_name}-{config.version}"
    matching = [path for path in candidates if path.name.startswith(prefix)]
    if not matching:
        raise FileNotFoundError(
            f"No file matching '{prefix}*' under {dist_dir} (glob: {config.wheel_glob})"
        )
    return matching[0]


def uninstall_wheel(config: ReleaseConfig) -> None:
    """Uninstall the target package using pip."""
    run([*PIP, "uninstall", "-y", config.package_name_dash], check=True)


def build_wheel(config: ReleaseConfig) -> None:
    """Build a wheel for the target project."""
    run([PYTHON, "-m", "pip", "install", "--upgrade", "pip"], check=True, cwd=config.project_dir)
    run([PYTHON, "-m", "pip", "install", "--upgrade", "build"], check=True, cwd=config.project_dir)
    run([PYTHON, "-m", "build"], check=True, cwd=config.project_dir)


def install_wheel(config: ReleaseConfig) -> None:
    """Install the built wheel for the target project."""
    run([*PIP, "install", str(resolve_wheel_path(config))], check=True)


def install_wheel_devmode(config: ReleaseConfig) -> None:
    """Install the target project in editable mode."""
    run([*PIP, "install", "-e", "."], check=True, cwd=config.project_dir)


def cleanup_old_wheels(config: ReleaseConfig) -> None:
    """Remove previously built wheels for the target package from dist/."""
    dist_dir = config.project_dir / "dist"
    if dist_dir.is_dir():
        for path in dist_dir.iterdir():
            if path.name.startswith(f"{config.package_name}-"):
                path.unlink()
