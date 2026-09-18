from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("release-saga")
except PackageNotFoundError:
    __version__ = "0.1.0"

from .cli import build_arg_parser, build_release_steps
from .config import ReleaseConfig, load_config, resolve_project_dir
from .pipeline import run_release_pipeline
from .steps import ReleaseStep

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
