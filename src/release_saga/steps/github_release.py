"""GitHub Release creation step for the release pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from subprocess import run
from tempfile import NamedTemporaryFile
from typing import Any

from release_saga.config import ReleaseConfig
from release_saga.package_ops import command_ok, executable_exists, resolve_wheel_path
from release_saga.steps.base import ReleaseStep


class GitHubReleaseStep(ReleaseStep):
    """Create a GitHub Release for the configured version.

    :param config: Resolved release configuration for the target repository.
    """

    #: Human-readable step name used in pipeline logs.
    name = "create GitHub release"

    def __init__(self, config: ReleaseConfig):
        """Initialize the GitHub release step.

        :param config: Resolved release configuration for the target repository.
        """
        self.config = config
        self._created_release = False
        self._rollback_tag: str | None = None

    def _tag(self) -> str:
        """Render the git tag name for the configured release.

        :returns: Tag name built from ``config.git_tag_template``.
        """
        return self.config.git_tag_template.format(version=self.config.version)

    def _release_notes_path(self) -> Path:
        """Resolve the path to the release-notes JSON file.

        :returns: Absolute path to the configured release-notes file.
        """
        return self.config.project_dir / self.config.release_notes_path

    def _release_notes(self) -> dict[str, object]:
        """Load the release-notes JSON document.

        :returns: Parsed release-notes data.
        """
        with self._release_notes_path().open(encoding="utf-8") as release_json:
            return json.load(release_json)

    def release_version_exists(self) -> bool:
        """Check whether release notes exist for the configured version.

        :returns: ``True`` when ``RELEASE_NOTES.json`` contains the current version.
        """
        release_notes = self._release_notes()
        releases = release_notes.get("releases", {})
        return self.config.version in releases

    def tmp_release_notes(self) -> Path:
        """Create a temporary Markdown file for GitHub release notes.

        :raises SystemExit: If release notes for the configured version are missing.
        :returns: Path to the temporary Markdown file.
        """
        release_notes = self._release_notes()
        if not self.release_version_exists():
            print(f"No release notes found for version {self.config.version}")
            raise SystemExit(1)

        last_release = release_notes["releases"][self.config.version]["release_notes"]
        url_template = release_notes["release"]["download_link"]
        release_url = url_template.format(
            version=self.config.version,
            package_name=self.config.package_name,
            package_name_dash=self.config.package_name_dash,
        )
        print(f"Last release notes: {last_release}")
        print(f"Download URL template: {url_template}")
        print(f"Download URL: {release_url}")

        with NamedTemporaryFile(
            "w",
            delete=False,
            dir=self.config.project_dir,
            suffix=".md",
            encoding="utf-8",
        ) as release_tmp:
            release_tmp.write("## Release notes\n")
            for note in last_release:
                release_tmp.write(f"* {note}\n")
            release_tmp.write("## Staging Area Download URL\n")
            release_tmp.write(f"[Wheel Package {self.config.version} on AWS S3]({release_url})\n")
            return Path(release_tmp.name)

    def check(self) -> str | None:
        """Check that GitHub release creation can proceed safely.

        :returns: ``None`` when release creation can proceed, otherwise a blocking reason.
        """
        if not executable_exists("gh"):
            return "GitHub CLI (gh) not installed"
        if not command_ok(["gh", "auth", "status"], cwd=self.config.project_dir):
            return "gh is not logged in (run `gh auth login`)"
        if command_ok(["gh", "release", "view", self._tag()], cwd=self.config.project_dir):
            return f"GitHub release '{self._tag()}' already exists"
        if not self.release_version_exists():
            return (
                f"no release notes found for version {self.config.version} "
                f"in {self.config.release_notes_path}"
            )
        return None

    def execute(self):
        """Create the GitHub Release and attach the built wheel.

        :raises CalledProcessError: If the GitHub CLI fails while creating the release.
        """
        release_file = self.tmp_release_notes()
        try:
            run(
                [
                    "gh",
                    "release",
                    "create",
                    self._tag(),
                    str(resolve_wheel_path(self.config)),
                    "--title",
                    self.config.version,
                    "--notes-file",
                    str(release_file),
                ],
                check=True,
                cwd=self.config.project_dir,
            )
            self._created_release = True
        finally:
            release_file.unlink(missing_ok=True)

    def recovery_data(self) -> dict[str, Any]:
        """Capture the release tag needed by a later clean operation."""
        return {"tag": self._tag()}

    def prepare_rollback(self, recovery_data: dict[str, Any]):
        """Restore successful release creation state from persisted history."""
        self._rollback_tag = str(recovery_data["tag"])
        self._created_release = True

    def rollback(self):
        """Delete the GitHub Release created by this run, if any.

        :raises CalledProcessError: If the GitHub CLI fails while deleting the release.
        """
        tag = self._rollback_tag or self._tag()
        rollback_may_be_unapplied = getattr(self, "_rollback_may_be_unapplied", False)
        if self._created_release and (
            not rollback_may_be_unapplied
            or command_ok(["gh", "release", "view", tag], cwd=self.config.project_dir)
        ):
            run(
                ["gh", "release", "delete", tag, "--yes"],
                check=True,
                cwd=self.config.project_dir,
            )
