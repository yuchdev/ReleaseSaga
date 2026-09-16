from __future__ import annotations

from subprocess import run

from ..config import ReleaseConfig
from ..package_ops import command_ok, executable_exists
from .base import ReleaseStep


class GitTagStep(ReleaseStep):
    name = "tag release in git"

    def __init__(self, config: ReleaseConfig):
        self.config = config
        self._created_local_tag = False
        self._pushed_remote_tag = False

    def _tag(self) -> str:
        return self.config.git_tag_template.format(version=self.config.version)

    def check(self) -> str | None:
        tag = self._tag()
        if not executable_exists("git"):
            return "git not installed"
        if not command_ok(
            ["git", "remote", "get-url", self.config.git_remote],
            cwd=self.config.project_dir,
        ):
            return f"no '{self.config.git_remote}' remote configured for this repository"
        if command_ok(
            ["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"],
            cwd=self.config.project_dir,
        ):
            return f"git tag '{tag}' already exists locally"
        if command_ok(
            ["git", "ls-remote", "--exit-code", "--tags", self.config.git_remote, tag],
            cwd=self.config.project_dir,
        ):
            return f"git tag '{tag}' already exists on remote '{self.config.git_remote}'"
        return None

    def execute(self) -> None:
        tag = self._tag()
        run(
            ["git", "tag", "-a", tag, "-m", f"Release {self.config.version}"],
            check=True,
            cwd=self.config.project_dir,
        )
        self._created_local_tag = True
        run(
            ["git", "push", self.config.git_remote, f"refs/tags/{tag}"],
            check=True,
            cwd=self.config.project_dir,
        )
        self._pushed_remote_tag = True

    def rollback(self) -> None:
        tag = self._tag()
        if self._pushed_remote_tag:
            run(
                ["git", "push", self.config.git_remote, f":refs/tags/{tag}"],
                check=True,
                cwd=self.config.project_dir,
            )
        if self._created_local_tag:
            run(["git", "tag", "-d", tag], check=True, cwd=self.config.project_dir)
