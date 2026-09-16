from __future__ import annotations

from pathlib import Path
from subprocess import run

from ..config import ReleaseConfig
from ..package_ops import PIP, executable_exists
from ..pipeline import _log
from .base import ReleaseStep


class PublishPyPiStep(ReleaseStep):
    name = "publish to PyPI"

    def __init__(self, config: ReleaseConfig):
        self.config = config

    def check(self) -> str | None:
        if not executable_exists("twine"):
            return "twine not installed"
        if not (Path.home() / ".pypirc").is_file():
            return "no ~/.pypirc file found"
        return None

    def execute(self) -> None:
        distributions = sorted(
            str(path)
            for path in self.config.project_dir.glob(self.config.wheel_glob)
            if path.is_file()
        )
        if not distributions:
            raise FileNotFoundError(
                f"No distributions found for '{self.config.wheel_glob}' "
                f"in {self.config.project_dir}"
            )
        run(
            [*PIP, "install", "--upgrade", "build", "twine"],
            check=True,
            cwd=self.config.project_dir,
        )
        run(["twine", "check", *distributions], check=True, cwd=self.config.project_dir)
        run(["twine", "upload", *distributions], check=True, cwd=self.config.project_dir)

    def rollback(self) -> None:
        _log(
            f"WARNING: cannot auto-rollback a PyPI publish. If {self.config.package_name}=="
            f"{self.config.version} was actually uploaded, yank it manually at "
            f"https://pypi.org/manage/project/{self.config.package_name_dash}/release/{self.config.version}/"
        )
