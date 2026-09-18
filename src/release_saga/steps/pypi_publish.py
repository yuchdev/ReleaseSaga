"""PyPI publishing step for the release pipeline."""

from __future__ import annotations

from pathlib import Path
from subprocess import run
from typing import Optional

from release_saga.config import ReleaseConfig
from release_saga.package_ops import PIP, executable_exists
from release_saga.steps.base import ReleaseStep


class PublishPyPiStep(ReleaseStep):
    """Publish built distributions to PyPI.

    :param config: Resolved release configuration for the target project.
    """

    #: Human-readable step name used in pipeline logs.
    name = "publish to PyPI"

    def __init__(self, config: ReleaseConfig):
        """Initialize the PyPI publishing step.

        :param config: Resolved release configuration for the target project.
        """
        self.config = config

    def check(self) -> Optional[str]:
        """Check that PyPI publishing prerequisites are available.

        :returns: ``None`` when publishing can proceed, otherwise a blocking reason.
        """
        if not executable_exists("twine"):
            return "twine not installed"
        if not (Path.home() / ".pypirc").is_file():
            return "no ~/.pypirc file found"
        return None

    def execute(self):
        """Validate and upload configured distribution files to PyPI.

        :raises FileNotFoundError: If no distributions match ``config.publish_glob``.
        :raises CalledProcessError: If dependency installation, validation, or upload fails.
        """
        distributions = sorted(
            str(path) for path in self.config.project_dir.glob(self.config.publish_glob) if path.is_file()
        )
        if not distributions:
            raise FileNotFoundError(
                f"No distributions found for '{self.config.publish_glob}' in {self.config.project_dir}"
            )
        run(
            [*PIP, "install", "--upgrade", "build", "twine"],
            check=True,
            cwd=self.config.project_dir,
        )
        run(["twine", "check", *distributions], check=True, cwd=self.config.project_dir)
        run(["twine", "upload", *distributions], check=True, cwd=self.config.project_dir)

    def rollback(self):
        """Log manual cleanup instructions for an irreversible PyPI upload."""
        from ..pipeline import _log

        _log(
            f"WARNING: cannot auto-rollback a PyPI publish. If {self.config.package_name}=="
            f"{self.config.version} was actually uploaded, yank it manually at "
            f"https://pypi.org/manage/project/{self.config.package_name_dash}/release/{self.config.version}/"
        )
