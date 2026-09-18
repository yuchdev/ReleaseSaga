from __future__ import annotations

import json
from pathlib import Path
from subprocess import run

from .config import ReleaseConfig
from .package_ops import executable_exists


def _pyproject_path(project_dir: Path) -> Path:
    return project_dir / "pyproject.toml"


def _set_pyproject_version(project_dir: Path, new_version: str) -> None:
    """Rewrite only the `version = "..."` value in [project], preserving everything else."""
    path = _pyproject_path(project_dir)
    if not path.is_file():
        raise RuntimeError(f"Cannot find {path}")
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

    in_project_table = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "[project]":
            in_project_table = True
            continue
        if in_project_table and stripped.startswith("[") and not stripped.startswith("[["):
            break
        if in_project_table and stripped.startswith("version") and "=" in stripped:
            prefix = line[: line.index("=") + 1]
            newline = "\n" if line.endswith("\n") else ""
            lines[index] = f'{prefix} "{new_version}"{newline}'
            path.write_text("".join(lines), encoding="utf-8")
            return

    raise RuntimeError(f"Could not find 'version' in [project] table of {path}")


def _load_release_notes(release_notes_path: Path) -> dict[str, object]:
    if not release_notes_path.is_file():
        raise RuntimeError(f"Cannot find {release_notes_path}")
    with release_notes_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _check_release_notes_entry_absent(release_notes_path: Path, new_version: str) -> None:
    release_notes = _load_release_notes(release_notes_path)
    releases = release_notes.get("releases", {})
    if new_version in releases:
        raise RuntimeError(f"Version {new_version} already has an entry in {release_notes_path}")


def _add_release_notes_entry(release_notes_path: Path, new_version: str) -> None:
    release_notes = _load_release_notes(release_notes_path)
    releases = release_notes.setdefault("releases", {})
    releases[new_version] = {"release_notes": []}
    with release_notes_path.open("w", encoding="utf-8") as handle:
        json.dump(release_notes, handle, indent=2)
        handle.write("\n")


def _update_uv_lock(project_dir: Path) -> None:
    run(["uv", "lock"], check=True, cwd=project_dir)


def set_release_version(config: ReleaseConfig, new_version: str) -> None:
    """Set the release version in pyproject.toml and RELEASE_NOTES.json, then refresh uv.lock.

    Runs independently of the release pipeline: no rollback on failure, matching the other
    direct, one-shot operations in package_ops.py. Checks that can be done up front (release
    notes entry absent, uv installed) run before any file is written, so a foreseeable failure
    doesn't leave pyproject.toml and RELEASE_NOTES.json out of sync.
    """
    release_notes_path = config.project_dir / config.release_notes_path
    _check_release_notes_entry_absent(release_notes_path, new_version)
    if not executable_exists("uv"):
        raise RuntimeError("uv is not installed; cannot update uv.lock")

    _set_pyproject_version(config.project_dir, new_version)
    _add_release_notes_entry(release_notes_path, new_version)
    _update_uv_lock(config.project_dir)
