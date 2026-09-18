import json
from pathlib import Path
from typing import Optional

import pytest

from release_saga.config import ReleaseConfig
from release_saga.version_ops import set_release_version


def make_config(project_dir: Path, **overrides: Optional[str]) -> ReleaseConfig:
    values = {
        "project_dir": project_dir,
        "package_name": "demo_package",
        "package_name_dash": "demo-package",
        "version": "1.2.3",
        "release_notes_path": "RELEASE_NOTES.json",
    }
    values.update(overrides)
    return ReleaseConfig(**values)


def write_pyproject(project_dir: Path) -> None:
    (project_dir / "pyproject.toml").write_text(
        """
[project]
name = "demo-package"
version = "1.2.3"
description = "demo"

[project.urls]
Homepage = "https://example.com"

[tool.release-saga]
s3_bucket = "some-bucket"
""".lstrip(),
        encoding="utf-8",
    )


def write_release_notes(project_dir: Path, releases: dict) -> None:
    (project_dir / "RELEASE_NOTES.json").write_text(
        json.dumps({"release": {"download_link": "https://example.com/x"}, "releases": releases}, indent=2) + "\n",
        encoding="utf-8",
    )


def test_set_release_version_updates_pyproject_release_notes_and_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_pyproject(tmp_path)
    write_release_notes(tmp_path, {"1.2.3": {"release_notes": ["First release."]}})
    config = make_config(tmp_path)
    commands: list[list[str]] = []

    monkeypatch.setattr("release_saga.version_ops.executable_exists", lambda executable: True)
    monkeypatch.setattr(
        "release_saga.version_ops.run",
        lambda cmd, **kwargs: commands.append(cmd),
    )

    set_release_version(config, "1.3.0")

    pyproject_text = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "1.3.0"' in pyproject_text
    assert "[project.urls]" in pyproject_text
    assert 's3_bucket = "some-bucket"' in pyproject_text

    release_notes = json.loads((tmp_path / "RELEASE_NOTES.json").read_text(encoding="utf-8"))
    assert release_notes["releases"]["1.2.3"]["release_notes"] == ["First release."]
    assert release_notes["releases"]["1.3.0"]["release_notes"] == []

    assert commands == [["uv", "lock"]]


def test_set_release_version_raises_when_uv_missing_and_does_not_modify_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_pyproject(tmp_path)
    write_release_notes(tmp_path, {"1.2.3": {"release_notes": []}})
    config = make_config(tmp_path)

    monkeypatch.setattr("release_saga.version_ops.executable_exists", lambda executable: False)

    with pytest.raises(RuntimeError, match="uv is not installed"):
        set_release_version(config, "1.3.0")

    pyproject_text = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "1.2.3"' in pyproject_text


def test_set_release_version_raises_when_entry_already_exists_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_pyproject(tmp_path)
    write_release_notes(tmp_path, {"1.3.0": {"release_notes": ["Already here."]}})
    config = make_config(tmp_path)
    commands: list[list[str]] = []

    monkeypatch.setattr("release_saga.version_ops.executable_exists", lambda executable: True)
    monkeypatch.setattr(
        "release_saga.version_ops.run",
        lambda cmd, **kwargs: commands.append(cmd),
    )

    with pytest.raises(RuntimeError, match="already has an entry"):
        set_release_version(config, "1.3.0")

    pyproject_text = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "1.2.3"' in pyproject_text
    assert commands == []


def test_set_release_version_raises_when_pyproject_missing_project_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[tool.release-saga]\ns3_bucket = "some-bucket"\n',
        encoding="utf-8",
    )
    write_release_notes(tmp_path, {})
    config = make_config(tmp_path)

    monkeypatch.setattr("release_saga.version_ops.executable_exists", lambda executable: True)
    monkeypatch.setattr("release_saga.version_ops.run", lambda cmd, **kwargs: None)

    with pytest.raises(RuntimeError, match="Could not find 'version'"):
        set_release_version(config, "1.3.0")
