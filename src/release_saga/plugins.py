"""Plugin loading for ReleaseSaga: entry points and root-file/module class references.

Two independent mechanisms let a target project add release steps *without* reimplementing
``release-saga``'s CLI:

1. **Entry points** — a pip-installable package registers ``ReleaseStep`` subclasses under the
   ``release_saga.steps`` entry-point group in its own ``pyproject.toml``. ``release-saga``
   discovers and instantiates them automatically whenever it runs against any target project that
   has that package installed. This is the right mechanism for a step meant to be shared/reused
   across projects.
2. **``extra_steps`` config** — a single target project lists ``"path_or_module:ClassName"``
   strings under ``[tool.release-saga] extra_steps`` in its own ``pyproject.toml``. Each string
   points at a ``ReleaseStep`` subclass either in a plain ``.py`` file relative to the project root
   (the default, no packaging required) or in an importable module. List order is the step's
   priority: entries run in the order they're listed. This is the right mechanism for a step that's
   specific to a single project and not worth publishing as a package.

Both mechanisms are additive to the built-in steps `build_release_steps()` wires up, and both are
independent of (and preferred over) hand-writing a wrapper script around
`run_release_pipeline()` — see ``docs/tutorials/custom-release-step.md`` for that older, still
supported, approach.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any

from release_saga.config import ReleaseConfig
from release_saga.steps.base import ReleaseStep

#: Entry-point group ``release-saga`` scans for installable plugin steps.
ENTRY_POINT_GROUP = "release_saga.steps"


class PluginLoadError(RuntimeError):
    """Raised when a configured or discovered plugin step cannot be loaded or instantiated."""


def _instantiate(step_class: Any, config: ReleaseConfig, source: str) -> ReleaseStep:
    """Instantiate a plugin-provided step class with the release configuration.

    :param step_class: Object resolved from a plugin spec or entry point.
    :param config: Resolved release configuration to hand to the step's constructor.
    :param source: Human-readable origin of ``step_class``, used in error messages.
    :raises PluginLoadError: If ``step_class`` isn't a ``ReleaseStep`` subclass, or can't be
        constructed with ``config`` as its only argument.
    :returns: The instantiated release step.
    """
    if not (isinstance(step_class, type) and issubclass(step_class, ReleaseStep)):
        raise PluginLoadError(f"{source} does not resolve to a ReleaseStep subclass (got {step_class!r})")
    try:
        return step_class(config)
    except TypeError as exc:
        raise PluginLoadError(f"Could not instantiate {source} with (config): {exc}") from exc


def _load_class_from_file(file_path: Path, class_name: str) -> Any:
    """Load a single attribute out of a standalone ``.py`` file.

    :param file_path: Absolute path to the plugin file.
    :param class_name: Name of the attribute (expected to be a class) to retrieve.
    :raises PluginLoadError: If the file is missing, fails to execute, or lacks the attribute.
    :returns: The resolved attribute.
    """
    if not file_path.is_file():
        raise PluginLoadError(f"Plugin file not found: {file_path}")
    module_name = f"_release_saga_plugin_{file_path.stem}_{abs(hash(str(file_path)))}"
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise PluginLoadError(f"Could not load plugin module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        del sys.modules[module_name]
        raise PluginLoadError(f"Error executing plugin file {file_path}: {exc}") from exc
    try:
        return getattr(module, class_name)
    except AttributeError as exc:
        raise PluginLoadError(f"{file_path} has no attribute '{class_name}'") from exc


def _load_class_from_module(module_name: str, class_name: str) -> Any:
    """Load a single attribute out of an importable module.

    :param module_name: Dotted module path to import.
    :param class_name: Name of the attribute (expected to be a class) to retrieve.
    :raises PluginLoadError: If the module can't be imported or lacks the attribute.
    :returns: The resolved attribute.
    """
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise PluginLoadError(f"Could not import plugin module '{module_name}': {exc}") from exc
    try:
        return getattr(module, class_name)
    except AttributeError as exc:
        raise PluginLoadError(f"Module '{module_name}' has no attribute '{class_name}'") from exc


def resolve_plugin_spec(spec: str, project_dir: Path) -> Any:
    """Resolve a ``"path_or_module:ClassName"`` plugin spec string to a class object.

    A location containing a path separator or ending in ``.py`` is treated as a file path
    (resolved relative to ``project_dir`` when not absolute) — this is the default way to add a
    single project-specific step, with no packaging required. Anything else is treated as a
    dotted, importable module path.

    :param spec: Plugin reference in the form ``"path_or_module:ClassName"``.
    :param project_dir: Target project directory used to resolve relative file paths.
    :raises PluginLoadError: If the spec is malformed or the class cannot be loaded.
    :returns: The resolved class object.
    """
    if ":" not in spec:
        raise PluginLoadError(f"Invalid plugin spec '{spec}': expected 'module_or_path:ClassName'")
    location, _, class_name = spec.rpartition(":")
    if not location or not class_name:
        raise PluginLoadError(f"Invalid plugin spec '{spec}': expected 'module_or_path:ClassName'")
    if location.endswith(".py") or "/" in location or "\\" in location:
        file_path = Path(location)
        if not file_path.is_absolute():
            file_path = project_dir / file_path
        return _load_class_from_file(file_path, class_name)
    return _load_class_from_module(location, class_name)


def load_configured_steps(config: ReleaseConfig, specs: tuple[str, ...] | list[str]) -> list[ReleaseStep]:
    """Instantiate release steps referenced by ``[tool.release-saga] extra_steps``.

    :param config: Resolved release configuration passed to each step's constructor.
    :param specs: Ordered plugin specs; list order is each step's priority/position in the
        pipeline relative to the other configured steps.
    :raises PluginLoadError: If any spec is malformed, unresolvable, or fails to instantiate.
    :returns: Release step instances, in the same order as ``specs``.
    """
    steps: list[ReleaseStep] = []
    for spec in specs:
        step_class = resolve_plugin_spec(spec, config.project_dir)
        steps.append(_instantiate(step_class, config, f"extra_steps entry '{spec}'"))
    return steps


def discover_entry_point_steps(config: ReleaseConfig, *, group: str = ENTRY_POINT_GROUP) -> list[ReleaseStep]:
    """Discover and instantiate release steps registered via packaging entry points.

    :param config: Resolved release configuration passed to each step's constructor.
    :param group: Entry-point group name to scan (defaults to ``release_saga.steps``).
    :raises PluginLoadError: If a discovered entry point cannot be loaded or instantiated.
    :returns: Release step instances, sorted by entry-point name for deterministic order.
    """
    from importlib.metadata import entry_points

    discovered = sorted(entry_points(group=group), key=lambda ep: ep.name)
    steps: list[ReleaseStep] = []
    for ep in discovered:
        try:
            step_class = ep.load()
        except Exception as exc:
            raise PluginLoadError(f"Could not load entry point '{ep.name}' ({ep.value}): {exc}") from exc
        steps.append(_instantiate(step_class, config, f"entry point '{ep.name}' ({ep.value})"))
    return steps


def load_plugin_steps(config: ReleaseConfig, *, include_entry_points: bool = True) -> list[ReleaseStep]:
    """Load all plugin-provided steps: configured ``extra_steps`` first, then entry points.

    :param config: Resolved release configuration passed to each step's constructor.
    :param include_entry_points: Whether to also discover installed entry-point steps; pass
        ``False`` (e.g. from a ``--no-plugins``-style flag) to only honor ``extra_steps``... or
        pass an already-filtered ``config.extra_steps`` and set this ``False`` to disable
        plugins entirely.
    :raises PluginLoadError: If any configured or discovered step cannot be loaded.
    :returns: Configured steps followed by discovered entry-point steps, in that order.
    """
    steps = load_configured_steps(config, config.extra_steps)
    if include_entry_points:
        steps.extend(discover_entry_point_steps(config))
    return steps
