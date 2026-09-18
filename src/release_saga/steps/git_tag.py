"""Git tag creation step for the release pipeline."""

from __future__ import annotations

from subprocess import run

from release_saga.config import ReleaseConfig
from release_saga.package_ops import command_ok, executable_exists
from release_saga.steps.base import ReleaseStep


class GitTagStep(ReleaseStep):
    """Create and push an annotated git tag for the current release.

    :param config: Resolved release configuration for the target repository.
    """

    #: Human-readable step name used in pipeline logs.
    name = "tag release in git"

    def __init__(self, config: ReleaseConfig):
        """Initialize the git tagging step.

        :param config: Resolved release configuration for the target repository.
        """
        self.config = config
        self._created_local_tag = False
        self._pushed_remote_tag = False

    def _tag(self) -> str:
        """Render the git tag name for the configured release.

        :returns: Tag name built from ``config.git_tag_template``.
        """
        return self.config.git_tag_template.format(version=self.config.version)

    def check(self) -> str | None:
        """Check that git tagging can proceed safely.

        :returns: ``None`` when tagging can proceed, otherwise a blocking reason.
        """
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

    def execute(self):
        """Create and push the release tag.

        :raises CalledProcessError: If git fails while creating or pushing the tag.
        """
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

    def rollback(self):
        """Delete any local or remote tag created by this run.

        :raises CalledProcessError: If git fails while deleting a created tag.
        """
        tag = self._tag()
        if self._pushed_remote_tag:
            run(
                ["git", "push", self.config.git_remote, f":refs/tags/{tag}"],
                check=True,
                cwd=self.config.project_dir,
            )
        if self._created_local_tag:
            run(["git", "tag", "-d", tag], check=True, cwd=self.config.project_dir)
