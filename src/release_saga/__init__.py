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
]
