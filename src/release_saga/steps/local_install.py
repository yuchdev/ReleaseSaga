"""Local installation step for the release pipeline."""

from __future__ import annotations

import sys
from typing import Any, Optional

from release_saga.config import ReleaseConfig
from release_saga.package_ops import (
    PIP,
    command_ok,
    install_wheel,
    install_wheel_devmode,
    resolve_wheel_path,
    uninstall_wheel,
)
from release_saga.steps.base import ReleaseStep


def _log(message: str):
    """Write a local-install log message to standard error, matching the pipeline's prefix.

    :param message: Human-readable message to emit.
    """
    print(f"[release] {message}", file=sys.stderr)


class LocalInstallStep(ReleaseStep):
    """Install or upgrade the target package into the interpreter running ReleaseSaga.

    In the default wheel mode the freshly built wheel is (re)installed and rollback uninstalls
    it. In development mode the project is installed in editable mode instead, and rollback
    deliberately keeps that editable install regardless of the release result.

    :param config: Resolved release configuration for the target project.
    :param dev_mode: Whether to install in editable (development) mode.
    """

    #: Human-readable step name used in pipeline logs.
    name = "install package locally"

    def __init__(self, config: ReleaseConfig, dev_mode: bool = False):
        """Initialize the local installation step.

        :param config: Resolved release configuration for the target project.
        :param dev_mode: Whether to install in editable (development) mode.
        """
        self.config = config
        self.dev_mode = dev_mode
        if dev_mode:
            self.name = "install package locally (development mode)"
        self._installed = False

    def check(self) -> Optional[str]:
        """Check that a wheel is available to install.

        :returns: ``None`` when installation can proceed, otherwise a blocking reason.
        """
        if self.dev_mode:
            return None
        try:
            resolve_wheel_path(self.config)
        except FileNotFoundError as exc:
            return str(exc)
        return None

    def execute(self):
        """Install the built wheel, or the project in editable mode when in development mode.

        :raises FileNotFoundError: If no matching wheel is available to install.
        :raises CalledProcessError: If the pip installation command fails.
        """
        if self.dev_mode:
            _log(
                f"Development in progress: installing {self.config.package_name_dash} "
                f"{self.config.version} in editable mode"
            )
            install_wheel_devmode(self.config)
            return
        install_wheel(self.config)
        self._installed = True

    def recovery_data(self) -> dict[str, Any]:
        """Capture the install mode needed by a later clean operation."""
        return {"dev_mode": self.dev_mode}

    def prepare_rollback(self, recovery_data: dict[str, Any]):
        """Restore install state for a run recorded by an earlier process."""
        self.dev_mode = bool(recovery_data.get("dev_mode", self.dev_mode))
        self._installed = True

    def rollback(self):
        """Uninstall the wheel installed by this run; keep an editable install in development mode.

        :raises CalledProcessError: If the pip uninstall command fails.
        """
        if self.dev_mode:
            _log(f"Development mode: keeping editable install of {self.config.package_name_dash}")
            return
        if not self._installed:
            return
        rollback_may_be_unapplied = getattr(self, "_rollback_may_be_unapplied", False)
        if rollback_may_be_unapplied and not command_ok([*PIP, "show", self.config.package_name_dash]):
            return
        uninstall_wheel(self.config)
