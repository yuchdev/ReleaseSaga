"""Configuration loading for ReleaseSaga target projects."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class ReleaseConfig:
    """Resolved release configuration for a target project.

    :param project_dir: Absolute path to the target project directory.
    :param package_name: Import-friendly package name with hyphens normalized to underscores.
    :param package_name_dash: Distribution-friendly package name with underscores normalized to hyphens.
    :param version: Release version read from the target project metadata.
    :param wheel_glob: Glob used to locate built wheel artifacts.
    :param publish_glob: Glob used to collect distribution files for publishing.
    :param s3_bucket: Bucket name for S3 uploads, when that release step is enabled.
    :param s3_prefix: Format string used to build the destination S3 key prefix.
    :param git_tag_template: Format string used to build the git tag name.
    :param git_remote: Git remote name used for tag pushes.
    :param release_notes_path: Relative path to the release-notes JSON file.
    """
    project_dir: Path
    package_name: str
    package_name_dash: str
    version: str
    wheel_glob: str = "dist/*.whl"
    publish_glob: str = "dist/*"
    s3_bucket: Optional[str] = None
    s3_prefix: str = "{package_name_dash}/"
    git_tag_template: str = "v{version}"
    git_remote: str = "origin"
    release_notes_path: str = "RELEASE_NOTES.json"


def resolve_project_dir(explicit: Optional[Path]) -> Path:
    """Resolve the target project directory for the current command.

    :param explicit: User-supplied project directory, if one was provided.
    :returns: Absolute path to the directory containing the target project's files.
    """
    if explicit is not None:
        return explicit.resolve()
    return Path.cwd().resolve()


def _load_pyproject(project_dir: Path) -> dict[str, Any]:
    """Load the target project's ``pyproject.toml`` file.

    :param project_dir: Directory expected to contain ``pyproject.toml``.
    :raises RuntimeError: If the file does not exist.
    :returns: Parsed TOML document.
    """
    pyproject_path = project_dir / "pyproject.toml"
    if not pyproject_path.is_file():
        raise RuntimeError(f"Cannot find {pyproject_path}")
    with pyproject_path.open("rb") as handle:
        return tomllib.load(handle)


def load_config(project_dir: Path, cli_overrides: dict[str, Any]) -> ReleaseConfig:
    """Load release configuration from ``pyproject.toml`` and CLI overrides.

    :param project_dir: Directory containing the target project metadata.
    :param cli_overrides: Explicit configuration overrides supplied by the CLI.
    :raises RuntimeError: If required metadata is missing or the tool configuration is invalid.
    :returns: Fully resolved release configuration.
    """
    data = _load_pyproject(project_dir)
    project = data.get("project", {})
    package_name = project.get("name")
    version = project.get("version")
    if not package_name or not version:
        pyproject_path = project_dir / "pyproject.toml"
        raise RuntimeError(f"'name' and 'version' must be present in [project] of {pyproject_path}")

    tool_table = data.get("tool", {}).get("release-saga", {})
    if tool_table is None:
        tool_table = {}
    if not isinstance(tool_table, dict):
        raise RuntimeError("[tool.release-saga] must be a table")

    values: dict[str, Any] = {
        "wheel_glob": "dist/*.whl",
        "publish_glob": "dist/*",
        "s3_bucket": None,
        "s3_prefix": "{package_name_dash}/",
        "git_tag_template": "v{version}",
        "git_remote": "origin",
        "release_notes_path": "RELEASE_NOTES.json",
    }
    for source in (tool_table, cli_overrides):
        for key, value in source.items():
            if key in values and value is not None:
                values[key] = value

    package_name_text = str(package_name)
    version_text = str(version)
    return ReleaseConfig(
        project_dir=project_dir.resolve(),
        package_name=package_name_text.replace("-", "_"),
        package_name_dash=package_name_text.replace("_", "-"),
        version=version_text,
        **values,
    )
