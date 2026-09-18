from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

from .config import ReleaseConfig, load_config, resolve_project_dir
from .package_ops import (
    build_wheel,
    cleanup_old_wheels,
    install_wheel,
    install_wheel_devmode,
    sanity_check,
    uninstall_wheel,
)
from .pipeline import run_release_pipeline
from .steps.base import ReleaseStep
from .steps.git_tag import GitTagStep
from .steps.github_release import GitHubReleaseStep
from .steps.pypi_publish import PublishPyPiStep
from .steps.s3 import UploadS3Step
from .version_ops import set_release_version


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Command-line params")
    parser.add_argument(
        "--mode",
        help="What to do with the package",
        choices=["build", "install", "dev", "reinstall", "uninstall", "set-version"],
        default="reinstall",
        required=False,
    )
    parser.add_argument(
        "--version",
        help="Print the target project's current version (from its pyproject.toml) and exit",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "--new-version",
        help="Version to write when --mode is 'set-version'",
        default=None,
        required=False,
    )
    parser.add_argument(
        "--upload-s3",
        help="Upload the package to S3",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "--create-release",
        help="Create a release on GitHub",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "--publish-pypi",
        help="Publish the package to PyPI server",
        action="store_true",
        default=False,
        required=False,
    )
    parser.add_argument("--project-dir", type=Path, default=None)
    parser.add_argument("--wheel-glob", default=None)
    parser.add_argument("--publish-glob", default=None)
    parser.add_argument("--s3-bucket", default=None)
    parser.add_argument("--s3-prefix", default=None)
    parser.add_argument("--git-tag-template", default=None)
    parser.add_argument("--git-remote", default=None)
    parser.add_argument("--release-notes-path", default=None)
    return parser


def build_release_steps(
    config: ReleaseConfig,
    *,
    upload_s3: bool,
    create_release: bool,
    publish_pypi: bool,
) -> list[ReleaseStep]:
    """Assemble the built-in release steps selected by CLI flags, in pipeline order."""
    steps: list[ReleaseStep] = []
    if upload_s3:
        steps.append(UploadS3Step(config))
    if create_release:
        steps.append(GitTagStep(config))
        steps.append(GitHubReleaseStep(config))
    if publish_pypi:
        steps.append(PublishPyPiStep(config))
    return steps


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    project_dir = resolve_project_dir(args.project_dir)

    if args.version:
        config = load_config(project_dir, {})
        print(config.version)
        return 0

    if args.mode == "set-version" and not args.new_version:
        parser.error("--new-version is required when --mode is 'set-version'")

    cli_overrides = {
        key: value
        for key, value in {
            "wheel_glob": args.wheel_glob,
            "publish_glob": args.publish_glob,
            "s3_bucket": args.s3_bucket,
            "s3_prefix": args.s3_prefix,
            "git_tag_template": args.git_tag_template,
            "git_remote": args.git_remote,
            "release_notes_path": args.release_notes_path,
        }.items()
        if value is not None
    }
    config = load_config(project_dir, cli_overrides)

    if args.mode == "set-version":
        set_release_version(config, args.new_version)
        print(f"Set version to {args.new_version}")
        return 0

    print(f"Package name: {config.package_name}")
    print(f"Package name2: {config.package_name_dash}")
    print(f"Version: {config.version}")
    sanity_check(config)

    if args.mode == "build":
        build_wheel(config)
    elif args.mode == "install":
        cleanup_old_wheels(config)
        build_wheel(config)
        install_wheel(config)
    elif args.mode == "dev":
        cleanup_old_wheels(config)
        build_wheel(config)
        install_wheel_devmode(config)
    elif args.mode == "reinstall":
        cleanup_old_wheels(config)
        uninstall_wheel(config)
        build_wheel(config)
        install_wheel(config)
    elif args.mode == "uninstall":
        uninstall_wheel(config)

    if args.mode != "uninstall":
        steps = build_release_steps(
            config,
            upload_s3=args.upload_s3,
            create_release=args.create_release,
            publish_pypi=args.publish_pypi,
        )
        if steps:
            run_release_pipeline(steps)

    return 0
