from __future__ import annotations

import json
from pathlib import Path
from subprocess import run
from tempfile import NamedTemporaryFile

from ..config import ReleaseConfig
from ..package_ops import command_ok, executable_exists, resolve_wheel_path
from .base import ReleaseStep


class GitHubReleaseStep(ReleaseStep):
    name = "create GitHub release"

    def __init__(self, config: ReleaseConfig):
        self.config = config

    def _tag(self) -> str:
        return self.config.git_tag_template.format(version=self.config.version)

    def _release_notes_path(self) -> Path:
        return self.config.project_dir / self.config.release_notes_path

    def _release_notes(self) -> dict[str, object]:
        with self._release_notes_path().open(encoding="utf-8") as release_json:
            return json.load(release_json)

    def release_version_exists(self) -> bool:
        release_notes = self._release_notes()
        releases = release_notes.get("releases", {})
        return self.config.version in releases

    def tmp_release_notes(self) -> Path:
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
        if not executable_exists("gh"):
            return "GitHub CLI (gh) not installed"
        if not command_ok(["gh", "auth", "status"]):
            return "gh is not logged in (run `gh auth login`)"
        if not self.release_version_exists():
            return (
                f"no release notes found for version {self.config.version} "
                f"in {self.config.release_notes_path}"
            )
        return None

    def execute(self) -> None:
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
        finally:
            release_file.unlink(missing_ok=True)

    def rollback(self) -> None:
        run(
            ["gh", "release", "delete", self._tag(), "--yes"],
            check=True,
            cwd=self.config.project_dir,
        )
