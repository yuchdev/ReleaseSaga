"""Package build, install, and artifact management helpers."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path
from subprocess import run

from release_saga.config import ReleaseConfig

#: Absolute path to the Python interpreter running ReleaseSaga.
PYTHON = sys.executable
#: Reusable ``python -m pip`` command prefix for package management subprocesses.
PIP = [PYTHON, "-m", "pip"]


def executable_exists(executable: str) -> bool:
    """Check whether an executable can be invoked on the current system.

    :param executable: Command name to probe.
    :returns: ``True`` when the command exists and reports a version successfully.
    """
    try:
        return run([executable, "--version"], capture_output=True).returncode == 0
    except FileNotFoundError:
        return False


def command_ok(cmd: Sequence[str], cwd: Path | None = None) -> bool:
    """Check whether a subprocess command exits successfully.

    :param cmd: Command and arguments to execute.
    :param cwd: Working directory for the subprocess, if needed.
    :returns: ``True`` when the command exists and exits with status code ``0``.
    """
    try:
        return run(list(cmd), capture_output=True, cwd=cwd).returncode == 0
    except FileNotFoundError:
        return False


def ensure_pip():
    """Make sure ``pip`` is importable by the interpreter running ReleaseSaga.

    Virtual environments created by ``uv venv``/``uv sync`` ship without ``pip``, so every
    ``python -m pip`` call would fail with ``No module named pip``. In that case ``pip`` is
    bootstrapped from the interpreter's bundled wheel via ``ensurepip``.

    :raises CalledProcessError: If ``pip`` is missing and ``ensurepip`` fails to install it.
    """
    if not command_ok([*PIP, "--version"]):
        run([PYTHON, "-m", "ensurepip", "--upgrade"], check=True)


def sanity_check(config: ReleaseConfig):
    """Validate the expected source layout for the target project.

    :param config: Resolved release configuration to validate.
    :raises SystemExit: If the expected ``src/<package_name>`` directory is missing.
    """
    source_dir = config.project_dir / "src" / config.package_name
    if not source_dir.is_dir():
        print(f"Cannot find src/{config.package_name}")
        raise SystemExit(1)


def resolve_wheel_path(config: ReleaseConfig) -> Path:
    """Resolve the newest built wheel matching the configured package version.

    :param config: Resolved release configuration describing the artifact location.
    :raises FileNotFoundError: If no matching wheel exists under the configured glob.
    :returns: Path to the newest matching wheel artifact.
    """
    dist_dir = config.project_dir / "dist"
    candidates = sorted(
        (path for path in config.project_dir.glob(config.wheel_glob) if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    prefix = f"{config.package_name}-{config.version}-"
    matching = [path for path in candidates if path.name.startswith(prefix)]
    if not matching:
        raise FileNotFoundError(
            f"No file matching '{prefix}*' under {dist_dir} (glob: {config.wheel_glob})"
        )
    return matching[0]


def uninstall_wheel(config: ReleaseConfig):
    """Uninstall the target package using ``pip``.

    :param config: Resolved release configuration for the target package.
    :raises CalledProcessError: If the uninstall command fails.
    """
    ensure_pip()
    run([*PIP, "uninstall", "-y", config.package_name_dash], check=True)


def build_wheel(config: ReleaseConfig):
    """Build a wheel for the target project.

    :param config: Resolved release configuration for the target package.
    :raises CalledProcessError: If dependency installation or wheel building fails.
    """
    ensure_pip()
    run([*PIP, "install", "--upgrade", "pip"], check=True, cwd=config.project_dir)
    run([*PIP, "install", "--upgrade", "build"], check=True, cwd=config.project_dir)
    run([PYTHON, "-m", "build"], check=True, cwd=config.project_dir)


def install_wheel(config: ReleaseConfig):
    """Install or upgrade the target package from its newest built wheel.

    The package itself is force-reinstalled so that a rebuilt wheel replaces an installed one
    even when the version string is unchanged; a second plain install then pulls in any
    dependencies that are not yet satisfied, without reinstalling the ones that are.

    :param config: Resolved release configuration for the target package.
    :raises FileNotFoundError: If no matching wheel is available to install.
    :raises CalledProcessError: If an installation command fails.
    """
    ensure_pip()
    wheel = str(resolve_wheel_path(config))
    run([*PIP, "install", "--upgrade", "--force-reinstall", "--no-deps", wheel], check=True)
    run([*PIP, "install", wheel], check=True)


def install_wheel_devmode(config: ReleaseConfig):
    """Install the target project in editable mode.

    :param config: Resolved release configuration for the target package.
    :raises CalledProcessError: If the editable install command fails.
    """
    ensure_pip()
    run([*PIP, "install", "-e", "."], check=True, cwd=config.project_dir)


def cleanup_old_wheels(config: ReleaseConfig):
    """Remove previously built wheel artifacts for the target package.

    :param config: Resolved release configuration describing the target package.
    :raises OSError: If an existing wheel cannot be removed.
    """
    dist_dir = config.project_dir / "dist"
    if dist_dir.is_dir():
        for path in dist_dir.iterdir():
            if path.suffix == ".whl" and path.name.startswith(f"{config.package_name}-"):
                path.unlink()
