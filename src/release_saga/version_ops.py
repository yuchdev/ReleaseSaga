"""Version-bump helpers for target projects managed by ReleaseSaga."""

from __future__ import annotations

import json
from pathlib import Path
from subprocess import run

from release_saga.config import ReleaseConfig
from release_saga.package_ops import executable_exists


def _pyproject_path(project_dir: Path) -> Path:
    """Resolve the ``pyproject.toml`` path for a target project.

    :param project_dir: Target project directory.
    :returns: Absolute or relative path to ``pyproject.toml`` within that project.
    """
    return project_dir / "pyproject.toml"


def _set_pyproject_version(project_dir: Path, new_version: str):
    """Rewrite only the ``version = "..."`` value in ``[project]``.

    Preserves the rest of ``pyproject.toml`` unchanged.

    :param project_dir: Directory containing the target ``pyproject.toml`` file.
    :param new_version: Version string to write.
    :raises RuntimeError: If ``pyproject.toml`` or its ``[project].version`` entry is missing.
    """
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
    """Load the release-notes JSON document.

    :param release_notes_path: Path to the release-notes JSON file.
    :raises RuntimeError: If the file does not exist.
    :returns: Parsed release-notes data.
    """
    if not release_notes_path.is_file():
        raise RuntimeError(f"Cannot find {release_notes_path}")
    with release_notes_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _release_notes_entry_exists(release_notes_path: Path, version: str) -> bool:
    """Check whether release notes already exist for a version.

    :param release_notes_path: Path to the release-notes JSON file.
    :param version: Version string to look up.
    :returns: ``True`` when the release-notes file already contains ``version``.
    """
    release_notes = _load_release_notes(release_notes_path)
    releases = release_notes.get("releases", {})
    return version in releases


def _add_release_notes_entry(release_notes_path: Path, new_version: str):
    """Add a new release-notes entry ahead of all existing releases.

    :param release_notes_path: Path to the release-notes JSON file.
    :param new_version: Version string to insert.
    """
    release_notes = _load_release_notes(release_notes_path)
    existing_releases = release_notes.get("releases", {})
    release_notes["releases"] = {new_version: {"release_notes": []}, **existing_releases}
    with release_notes_path.open("w", encoding="utf-8") as handle:
        json.dump(release_notes, handle, indent=2)
        handle.write("\n")


def _update_uv_lock(project_dir: Path):
    """Refresh ``uv.lock`` after a version change.

    :param project_dir: Target project directory.
    :raises CalledProcessError: If ``uv lock`` fails.
    """
    run(["uv", "lock"], check=True, cwd=project_dir)


def set_release_version(config: ReleaseConfig, new_version: str):
    """Set the release version in pyproject.toml and RELEASE_NOTES.json, then refresh uv.lock.

    Runs independently of the release pipeline: no rollback on failure, matching the other
    direct, one-shot operations in package_ops.py. The one check that can be done up front (uv
    installed) runs before any file is written, so a foreseeable failure doesn't leave
    pyproject.toml and RELEASE_NOTES.json out of sync. If RELEASE_NOTES.json already has an entry
    for `new_version` (e.g. hand-written notes from an earlier run), that file is left untouched
    rather than overwritten — pyproject.toml and uv.lock are still updated.

    :param config: Resolved release configuration for the target project.
    :param new_version: Version string to write into the project metadata.
    :raises RuntimeError: If ``uv`` is unavailable or required metadata files are missing.
    :raises CalledProcessError: If ``uv lock`` fails.
    """
    release_notes_path = config.project_dir / config.release_notes_path
    if not executable_exists("uv"):
        raise RuntimeError("uv is not installed; cannot update uv.lock")

    _set_pyproject_version(config.project_dir, new_version)
    if _release_notes_entry_exists(release_notes_path, new_version):
        print(f"Version {new_version} already has an entry in {release_notes_path}; leaving it as-is")
    else:
        _add_release_notes_entry(release_notes_path, new_version)
    _update_uv_lock(config.project_dir)
