from pathlib import Path

import pytest

from release_saga.config import load_config, resolve_project_dir


def test_load_config_raises_when_pyproject_missing(tmp_path: Path):
    """[Local] load_config: raises when pyproject missing.

    Scenario:
        Focus on the `raises when pyproject missing` case for `load_config` and assert the expected outcome.

    Boundaries:
        Covers temporary local files, directories, or subprocess arguments without performing a real release.

    On failure, first check:
        The `load_config` branch for this case and the fixtures or monkeypatches that establish it.
    """
    with pytest.raises(RuntimeError, match="Cannot find"):
        load_config(tmp_path, {})


def test_load_config_raises_when_name_or_version_missing(tmp_path: Path):
    """[Local] load_config: raises when name or version missing.

    Scenario:
        Focus on the `raises when name or version missing` case for `load_config` and assert the expected outcome.

    Boundaries:
        Covers temporary local files, directories, or subprocess arguments without performing a real release.

    On failure, first check:
        The `load_config` branch for this case and the fixtures or monkeypatches that establish it.
    """
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "demo-package"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="must be present"):
        load_config(tmp_path, {})


def test_load_config_raises_when_tool_table_is_not_a_table(tmp_path: Path):
    """[Local] load_config: raises when tool table is not a table.

    Scenario:
        Focus on the `raises when tool table is not a table` case for `load_config` and assert the expected outcome.

    Boundaries:
        Covers temporary local files, directories, or subprocess arguments without performing a real release.

    On failure, first check:
        The `load_config` branch for this case and the fixtures or monkeypatches that establish it.
    """
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "demo-package"
version = "1.2.3"

[tool]
release-saga = "not-a-table"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="must be a table"):
        load_config(tmp_path, {})


def test_load_config_treats_none_tool_table_as_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """[Local] load_config: treats none tool table as empty.

    Scenario:
        Focus on the `treats none tool table as empty` case for `load_config` and assert the expected outcome.

    Boundaries:
        Covers temporary local files, directories, or subprocess arguments without performing a real release.

    On failure, first check:
        The `load_config` branch for this case and the fixtures or monkeypatches that establish it.
    """
    monkeypatch.setattr(
        "release_saga.config._load_pyproject",
        lambda project_dir: {
            "project": {"name": "demo-package", "version": "1.2.3"},
            "tool": {"release-saga": None},
        },
    )

    config = load_config(tmp_path, {})

    assert config.s3_bucket is None
    assert config.wheel_glob == "dist/*.whl"


def test_load_config_ignores_unknown_keys_and_none_overrides(tmp_path: Path):
    """[Local] load_config: ignores unknown keys and none overrides.

    Scenario:
        Focus on the `ignores unknown keys and none overrides` case for `load_config` and assert the expected outcome.

    Boundaries:
        Covers temporary local files, directories, or subprocess arguments without performing a real release.

    On failure, first check:
        The `load_config` branch for this case and the fixtures or monkeypatches that establish it.
    """
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "demo-package"
version = "1.2.3"

[tool.release-saga]
unknown_field = "ignored"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    config = load_config(tmp_path, {"wheel_glob": None, "another_unknown": "ignored"})

    assert config.wheel_glob == "dist/*.whl"


def write_pyproject(project_dir: Path):
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


def test_load_config_precedence(tmp_path: Path):
    """[Local] load_config: precedence.

    Scenario:
        Focus on the `precedence` case for `load_config` and assert the expected outcome.

    Boundaries:
        Covers temporary local files, directories, or subprocess arguments without performing a real release.

    On failure, first check:
        The `load_config` branch for this case and the fixtures or monkeypatches that establish it.
    """
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


def test_load_config_defaults_extra_steps_to_empty_tuple(tmp_path: Path):
    """[Local] load_config: defaults extra_steps to an empty tuple.

    Scenario:
        Focus on the `defaults extra_steps to an empty tuple` case for `load_config` and assert the expected outcome.

    Boundaries:
        Covers temporary local files, directories, or subprocess arguments without performing a real release.

    On failure, first check:
        The `load_config` branch for this case and the fixtures or monkeypatches that establish it.
    """
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "demo-package"
version = "1.2.3"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    config = load_config(tmp_path, {})

    assert config.extra_steps == ()


def test_load_config_reads_extra_steps_list_and_preserves_order(tmp_path: Path):
    """[Local] load_config: reads extra_steps list and preserves order.

    Scenario:
        Focus on the `reads extra_steps list and preserves order` case for `load_config` and assert the expected outcome.

    Boundaries:
        Covers temporary local files, directories, or subprocess arguments without performing a real release.

    On failure, first check:
        The `load_config` branch for this case and the fixtures or monkeypatches that establish it.
    """
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "demo-package"
version = "1.2.3"

[tool.release-saga]
extra_steps = ["release_steps.py:ChangelogStep", "release_steps.py:SlackNotifyStep"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    config = load_config(tmp_path, {})

    assert config.extra_steps == (
        "release_steps.py:ChangelogStep",
        "release_steps.py:SlackNotifyStep",
    )


def test_load_config_raises_when_extra_steps_is_not_a_list_of_strings(tmp_path: Path):
    """[Local] load_config: raises when extra_steps is not a list of strings.

    Scenario:
        Focus on the `raises when extra_steps is not a list of strings` case for `load_config` and assert the expected outcome.

    Boundaries:
        Covers temporary local files, directories, or subprocess arguments without performing a real release.

    On failure, first check:
        The `load_config` branch for this case and the fixtures or monkeypatches that establish it.
    """
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "demo-package"
version = "1.2.3"

[tool.release-saga]
extra_steps = [1, 2]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="extra_steps must be a list of strings"):
        load_config(tmp_path, {})


def test_resolve_project_dir_uses_explicit_or_cwd(tmp_path: Path, monkeypatch):
    """[Local] resolve_project_dir: uses explicit or cwd.

    Scenario:
        Focus on the `uses explicit or cwd` case for `resolve_project_dir` and assert the expected outcome.

    Boundaries:
        Covers temporary local files, directories, or subprocess arguments without performing a real release.

    On failure, first check:
        The `resolve_project_dir` branch for this case and the fixtures or monkeypatches that establish it.
    """
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    assert resolve_project_dir(None) == tmp_path.resolve()
    assert resolve_project_dir(other_dir) == other_dir.resolve()
