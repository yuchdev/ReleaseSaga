from __future__ import annotations

from subprocess import run

from ..config import ReleaseConfig
from ..package_ops import command_ok, executable_exists
from .base import ReleaseStep


class GitTagStep(ReleaseStep):
    name = "tag release in git"

    def __init__(self, config: ReleaseConfig):
        self.config = config

    def _tag(self) -> str:
        return self.config.git_tag_template.format(version=self.config.version)

    def _branch(self) -> str:
        if self.config.git_branch is not None:
            return self.config.git_branch
        result = run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            check=True,
            cwd=self.config.project_dir,
            text=True,
        )
        return result.stdout.strip()

    def check(self) -> str | None:
        if not executable_exists("git"):
            return "git not installed"
        if not command_ok(
            ["git", "remote", "get-url", self.config.git_remote],
            cwd=self.config.project_dir,
        ):
            return f"no '{self.config.git_remote}' remote configured for this repository"
        return None

    def execute(self) -> None:
        tag = self._tag()
        run(
            ["git", "tag", "-a", tag, "-m", f"Release {self.config.version}"],
            check=True,
            cwd=self.config.project_dir,
        )
        run(
            ["git", "push", self.config.git_remote, "--tags", self._branch()],
            check=True,
            cwd=self.config.project_dir,
        )

    def rollback(self) -> None:
        tag = self._tag()
        run(["git", "tag", "-d", tag], check=True, cwd=self.config.project_dir)
        run(
            ["git", "push", self.config.git_remote, f":refs/tags/{tag}"],
            check=True,
            cwd=self.config.project_dir,
        )
