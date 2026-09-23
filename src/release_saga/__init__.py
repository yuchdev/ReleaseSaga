"""Public package interface for ReleaseSaga."""

from importlib.metadata import PackageNotFoundError, version

#: Installed package version, or a fallback for local source checkouts.
try:
    __version__ = version("release-saga")
except PackageNotFoundError:
    __version__ = "0.9.0"

from .cli import build_arg_parser, build_release_steps
from .config import ReleaseConfig, load_config, resolve_project_dir
from .pipeline import run_release_pipeline
from .plugins import (
    PluginLoadError,
    discover_entry_point_steps,
    load_configured_steps,
    load_plugin_steps,
    resolve_plugin_spec,
)
from .steps import ReleaseStep

#: Symbols re-exported at the package root for public use.
__all__ = [
    "__version__",
    "ReleaseStep",
    "ReleaseConfig",
    "load_config",
    "resolve_project_dir",
    "run_release_pipeline",
    "build_arg_parser",
    "build_release_steps",
    "PluginLoadError",
    "load_plugin_steps",
    "load_configured_steps",
    "discover_entry_point_steps",
    "resolve_plugin_spec",
]
