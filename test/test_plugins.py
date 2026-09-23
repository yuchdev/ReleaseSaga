from pathlib import Path
from typing import Optional

import pytest

from release_saga.config import ReleaseConfig
from release_saga.plugins import (
    ENTRY_POINT_GROUP,
    PluginLoadError,
    discover_entry_point_steps,
    load_configured_steps,
    load_plugin_steps,
    resolve_plugin_spec,
)
from release_saga.steps.base import ReleaseStep


def make_config(project_dir: Path, **overrides: Optional[str]) -> ReleaseConfig:
    values = {
        "project_dir": project_dir,
        "package_name": "demo_package",
        "package_name_dash": "demo-package",
        "version": "1.2.3",
    }
    values.update(overrides)
    return ReleaseConfig(**values)


VALID_STEP_SOURCE = """
from release_saga.steps.base import ReleaseStep


class ChangelogStep(ReleaseStep):
    name = "update changelog"

    def __init__(self, config):
        self.config = config
        self.executed = False
        self.rolled_back = False

    def execute(self):
        self.executed = True

    def rollback(self):
        self.rolled_back = True


class NotAStep:
    pass
"""


def write_plugin_file(project_dir: Path, filename: str = "release_steps.py") -> Path:
    plugin_path = project_dir / filename
    plugin_path.write_text(VALID_STEP_SOURCE, encoding="utf-8")
    return plugin_path


def test_resolve_plugin_spec_loads_class_from_relative_file(tmp_path: Path):
    """[Unit] resolve_plugin_spec: loads a class from a project-relative .py file.

    Scenario:
        Focus on the `loads a class from a project-relative .py file` case for `resolve_plugin_spec` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `resolve_plugin_spec` branch for this case and the fixtures or monkeypatches that establish it.
    """
    write_plugin_file(tmp_path)

    step_class = resolve_plugin_spec("release_steps.py:ChangelogStep", tmp_path)

    assert step_class.__name__ == "ChangelogStep"
    assert issubclass(step_class, ReleaseStep)


def test_resolve_plugin_spec_loads_class_from_absolute_file(tmp_path: Path):
    """[Unit] resolve_plugin_spec: loads a class from an absolute .py file path.

    Scenario:
        Focus on the `loads a class from an absolute .py file path` case for `resolve_plugin_spec` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `resolve_plugin_spec` branch for this case and the fixtures or monkeypatches that establish it.
    """
    plugin_path = write_plugin_file(tmp_path)

    step_class = resolve_plugin_spec(f"{plugin_path}:ChangelogStep", tmp_path)

    assert step_class.__name__ == "ChangelogStep"


def test_resolve_plugin_spec_loads_class_from_importable_module(tmp_path: Path):
    """[Unit] resolve_plugin_spec: loads a class from a dotted module path.

    Scenario:
        Focus on the `loads a class from a dotted module path` case for `resolve_plugin_spec` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `resolve_plugin_spec` branch for this case and the fixtures or monkeypatches that establish it.
    """
    step_class = resolve_plugin_spec("release_saga.steps.git_tag:GitTagStep", tmp_path)

    assert step_class.__name__ == "GitTagStep"


def test_resolve_plugin_spec_raises_when_spec_is_malformed(tmp_path: Path):
    """[Unit] resolve_plugin_spec: raises when the spec has no ':' separator.

    Scenario:
        Focus on the `raises when the spec has no ':' separator` case for `resolve_plugin_spec` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `resolve_plugin_spec` branch for this case and the fixtures or monkeypatches that establish it.
    """
    with pytest.raises(PluginLoadError, match="expected 'module_or_path:ClassName'"):
        resolve_plugin_spec("release_steps.py", tmp_path)


def test_resolve_plugin_spec_raises_when_file_missing(tmp_path: Path):
    """[Unit] resolve_plugin_spec: raises when the referenced file doesn't exist.

    Scenario:
        Focus on the `raises when the referenced file doesn't exist` case for `resolve_plugin_spec` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `resolve_plugin_spec` branch for this case and the fixtures or monkeypatches that establish it.
    """
    with pytest.raises(PluginLoadError, match="not found"):
        resolve_plugin_spec("missing.py:ChangelogStep", tmp_path)


def test_resolve_plugin_spec_raises_when_file_has_no_such_class(tmp_path: Path):
    """[Unit] resolve_plugin_spec: raises when the file lacks the requested attribute.

    Scenario:
        Focus on the `raises when the file lacks the requested attribute` case for `resolve_plugin_spec` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `resolve_plugin_spec` branch for this case and the fixtures or monkeypatches that establish it.
    """
    write_plugin_file(tmp_path)

    with pytest.raises(PluginLoadError, match="has no attribute 'MissingStep'"):
        resolve_plugin_spec("release_steps.py:MissingStep", tmp_path)


def test_resolve_plugin_spec_raises_when_file_fails_to_execute(tmp_path: Path):
    """[Unit] resolve_plugin_spec: raises when the plugin file itself raises on import.

    Scenario:
        Focus on the `raises when the plugin file itself raises on import` case for `resolve_plugin_spec` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `resolve_plugin_spec` branch for this case and the fixtures or monkeypatches that establish it.
    """
    (tmp_path / "broken.py").write_text("raise ValueError('boom')\n", encoding="utf-8")

    with pytest.raises(PluginLoadError, match="Error executing plugin file"):
        resolve_plugin_spec("broken.py:AnyStep", tmp_path)


def test_resolve_plugin_spec_raises_when_module_not_importable(tmp_path: Path):
    """[Unit] resolve_plugin_spec: raises when the dotted module can't be imported.

    Scenario:
        Focus on the `raises when the dotted module can't be imported` case for `resolve_plugin_spec` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `resolve_plugin_spec` branch for this case and the fixtures or monkeypatches that establish it.
    """
    with pytest.raises(PluginLoadError, match="Could not import plugin module"):
        resolve_plugin_spec("no_such_module_at_all:ChangelogStep", tmp_path)


def test_load_configured_steps_instantiates_in_order(tmp_path: Path):
    """[Unit] load_configured_steps: instantiates steps preserving spec order.

    Scenario:
        Focus on the `instantiates steps preserving spec order` case for `load_configured_steps` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `load_configured_steps` branch for this case and the fixtures or monkeypatches that establish it.
    """
    write_plugin_file(tmp_path)
    config = make_config(tmp_path)

    steps = load_configured_steps(
        config,
        ("release_steps.py:ChangelogStep", "release_steps.py:ChangelogStep"),
    )

    assert len(steps) == 2
    assert all(step.name == "update changelog" for step in steps)


def test_load_configured_steps_raises_when_class_is_not_a_release_step(tmp_path: Path):
    """[Unit] load_configured_steps: raises when the resolved class isn't a ReleaseStep.

    Scenario:
        Focus on the `raises when the resolved class isn't a ReleaseStep` case for `load_configured_steps` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `load_configured_steps` branch for this case and the fixtures or monkeypatches that establish it.
    """
    write_plugin_file(tmp_path)
    config = make_config(tmp_path)

    with pytest.raises(PluginLoadError, match="does not resolve to a ReleaseStep subclass"):
        load_configured_steps(config, ("release_steps.py:NotAStep",))


def test_load_configured_steps_raises_when_constructor_rejects_config(tmp_path: Path):
    """[Unit] load_configured_steps: raises when the step can't be built from (config).

    Scenario:
        Focus on the `raises when the step can't be built from (config)` case for `load_configured_steps` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `load_configured_steps` branch for this case and the fixtures or monkeypatches that establish it.
    """
    (tmp_path / "bad_ctor.py").write_text(
        """
from release_saga.steps.base import ReleaseStep


class BadCtorStep(ReleaseStep):
    def __init__(self, config, extra_required_arg):
        pass

    def execute(self):
        pass

    def rollback(self):
        pass
""",
        encoding="utf-8",
    )
    config = make_config(tmp_path)

    with pytest.raises(PluginLoadError, match="Could not instantiate"):
        load_configured_steps(config, ("bad_ctor.py:BadCtorStep",))


def test_load_configured_steps_empty_specs_returns_empty_list(tmp_path: Path):
    """[Unit] load_configured_steps: empty specs returns an empty list.

    Scenario:
        Focus on the `empty specs returns an empty list` case for `load_configured_steps` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `load_configured_steps` branch for this case and the fixtures or monkeypatches that establish it.
    """
    config = make_config(tmp_path)

    assert load_configured_steps(config, ()) == []


class _FakeEntryPoint:
    def __init__(self, name: str, value: str, loader):
        self.name = name
        self.value = value
        self._loader = loader

    def load(self):
        return self._loader()


def test_discover_entry_point_steps_sorts_by_name_and_instantiates(tmp_path, monkeypatch):
    """[Unit] discover_entry_point_steps: sorts entry points by name and instantiates them.

    Scenario:
        Focus on the `sorts entry points by name and instantiates them` case for `discover_entry_point_steps` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `discover_entry_point_steps` branch for this case and the fixtures or monkeypatches that establish it.
    """
    from release_saga.steps.git_tag import GitTagStep
    from release_saga.steps.s3 import UploadS3Step

    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "demo_package-1.2.3-py3-none-any.whl").write_text("wheel", encoding="utf-8")

    fake_eps = [
        _FakeEntryPoint("zzz-step", "pkg:UploadS3Step", lambda: UploadS3Step),
        _FakeEntryPoint("aaa-step", "pkg:GitTagStep", lambda: GitTagStep),
    ]
    monkeypatch.setattr(
        "importlib.metadata.entry_points",
        lambda group=None: fake_eps if group == ENTRY_POINT_GROUP else [],
    )
    config = make_config(tmp_path)

    steps = discover_entry_point_steps(config)

    assert [type(step) for step in steps] == [GitTagStep, UploadS3Step]


def test_discover_entry_point_steps_raises_when_entry_point_fails_to_load(tmp_path, monkeypatch):
    """[Unit] discover_entry_point_steps: raises when an entry point fails to load.

    Scenario:
        Focus on the `raises when an entry point fails to load` case for `discover_entry_point_steps` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `discover_entry_point_steps` branch for this case and the fixtures or monkeypatches that establish it.
    """
    def broken_loader():
        raise ImportError("no such module")

    fake_eps = [_FakeEntryPoint("broken-step", "pkg.missing:Step", broken_loader)]
    monkeypatch.setattr(
        "importlib.metadata.entry_points",
        lambda group=None: fake_eps if group == ENTRY_POINT_GROUP else [],
    )
    config = make_config(tmp_path)

    with pytest.raises(PluginLoadError, match="Could not load entry point 'broken-step'"):
        discover_entry_point_steps(config)


def test_discover_entry_point_steps_raises_when_entry_point_is_not_a_release_step(tmp_path, monkeypatch):
    """[Unit] discover_entry_point_steps: raises when an entry point isn't a ReleaseStep subclass.

    Scenario:
        Focus on the `raises when an entry point isn't a ReleaseStep subclass` case for `discover_entry_point_steps` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `discover_entry_point_steps` branch for this case and the fixtures or monkeypatches that establish it.
    """
    fake_eps = [_FakeEntryPoint("not-a-step", "pkg:NotAStep", lambda: object)]
    monkeypatch.setattr(
        "importlib.metadata.entry_points",
        lambda group=None: fake_eps if group == ENTRY_POINT_GROUP else [],
    )
    config = make_config(tmp_path)

    with pytest.raises(PluginLoadError, match="does not resolve to a ReleaseStep subclass"):
        discover_entry_point_steps(config)


def test_discover_entry_point_steps_returns_empty_list_when_none_registered(tmp_path, monkeypatch):
    """[Unit] discover_entry_point_steps: returns an empty list when nothing is registered.

    Scenario:
        Focus on the `returns an empty list when nothing is registered` case for `discover_entry_point_steps` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `discover_entry_point_steps` branch for this case and the fixtures or monkeypatches that establish it.
    """
    monkeypatch.setattr("importlib.metadata.entry_points", lambda group=None: [])
    config = make_config(tmp_path)

    assert discover_entry_point_steps(config) == []


def test_load_plugin_steps_combines_configured_and_entry_point_steps(tmp_path, monkeypatch):
    """[Unit] load_plugin_steps: combines configured extra_steps then entry-point steps.

    Scenario:
        Focus on the `combines configured extra_steps then entry-point steps` case for `load_plugin_steps` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `load_plugin_steps` branch for this case and the fixtures or monkeypatches that establish it.
    """
    from release_saga.steps.git_tag import GitTagStep

    write_plugin_file(tmp_path)
    fake_eps = [_FakeEntryPoint("git-tag-plugin", "pkg:GitTagStep", lambda: GitTagStep)]
    monkeypatch.setattr(
        "importlib.metadata.entry_points",
        lambda group=None: fake_eps if group == ENTRY_POINT_GROUP else [],
    )
    config = make_config(tmp_path, extra_steps=("release_steps.py:ChangelogStep",))

    steps = load_plugin_steps(config)

    assert len(steps) == 2
    assert steps[0].name == "update changelog"
    assert isinstance(steps[1], GitTagStep)


def test_load_plugin_steps_skips_entry_points_when_disabled(tmp_path, monkeypatch):
    """[Unit] load_plugin_steps: skips entry-point discovery when include_entry_points is False.

    Scenario:
        Focus on the `skips entry-point discovery when include_entry_points is False` case for `load_plugin_steps` and assert the expected outcome.

    Boundaries:
        Covers one focused branch with pytest fixtures and patched collaborators instead of real external services.

    On failure, first check:
        The `load_plugin_steps` branch for this case and the fixtures or monkeypatches that establish it.
    """
    from release_saga.steps.git_tag import GitTagStep

    write_plugin_file(tmp_path)
    fake_eps = [_FakeEntryPoint("git-tag-plugin", "pkg:GitTagStep", lambda: GitTagStep)]
    monkeypatch.setattr(
        "importlib.metadata.entry_points",
        lambda group=None: fake_eps if group == ENTRY_POINT_GROUP else [],
    )
    config = make_config(tmp_path, extra_steps=("release_steps.py:ChangelogStep",))

    steps = load_plugin_steps(config, include_entry_points=False)

    assert len(steps) == 1
    assert steps[0].name == "update changelog"
