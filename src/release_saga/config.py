from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ReleaseConfig:
    project_dir: Path
    package_name: str
    package_name_dash: str
    version: str
    wheel_glob: str = "dist/*.whl"
    publish_glob: str = "dist/*"
    s3_bucket: str | None = None
    s3_prefix: str = "{package_name_dash}/"
    git_tag_template: str = "v{version}"
    git_remote: str = "origin"
    git_branch: str | None = None
    release_notes_path: str = "RELEASE_NOTES.json"


def resolve_project_dir(explicit: Path | None) -> Path:
    """Directory containing the target project's pyproject.toml."""
    if explicit is not None:
        return explicit.resolve()
    return Path.cwd().resolve()


def _load_pyproject(project_dir: Path) -> dict[str, Any]:
    pyproject_path = project_dir / "pyproject.toml"
    if not pyproject_path.is_file():
        raise RuntimeError(f"Cannot find {pyproject_path}")
    with pyproject_path.open("rb") as handle:
        return tomllib.load(handle)


def load_config(project_dir: Path, cli_overrides: dict[str, Any]) -> ReleaseConfig:
    """Load release configuration from pyproject.toml and CLI overrides."""
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
        "git_branch": None,
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
