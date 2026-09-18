from pathlib import Path

from release_saga.config import load_config, resolve_project_dir


def write_pyproject(project_dir: Path) -> None:
    (project_dir / "pyproject.toml").write_text(
        """
[project]
name = "demo-package"
version = "1.2.3"

[tool.release-saga]
wheel_glob = "custom/*.whl"
publish_glob = "custom/dist/*"
s3_bucket = "bucket-from-pyproject"
git_tag_template = "release.{version}"
git_remote = "upstream"
release_notes_path = "notes.json"
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_load_config_precedence(tmp_path: Path) -> None:
    write_pyproject(tmp_path)

    config = load_config(
        tmp_path,
        {
            "wheel_glob": "override/*.whl",
            "publish_glob": "override/dist/*",
            "git_remote": "origin",
            "s3_prefix": "custom/{package_name_dash}/",
        },
    )

    assert config.project_dir == tmp_path.resolve()
    assert config.package_name == "demo_package"
    assert config.package_name_dash == "demo-package"
    assert config.version == "1.2.3"
    assert config.wheel_glob == "override/*.whl"
    assert config.publish_glob == "override/dist/*"
    assert config.s3_bucket == "bucket-from-pyproject"
    assert config.s3_prefix == "custom/{package_name_dash}/"
    assert config.git_tag_template == "release.{version}"
    assert config.git_remote == "origin"
    assert config.release_notes_path == "notes.json"


def test_resolve_project_dir_uses_explicit_or_cwd(tmp_path: Path, monkeypatch) -> None:
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    assert resolve_project_dir(None) == tmp_path.resolve()
    assert resolve_project_dir(other_dir) == other_dir.resolve()
