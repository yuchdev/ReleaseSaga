from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from .config import load_config, resolve_project_dir
from .package_ops import (
    build_wheel,
    cleanup_old_wheels,
    install_wheel,
    install_wheel_devmode,
    sanity_check,
    uninstall_wheel,
)
from .pipeline import run_release_pipeline
from .steps.git_tag import GitTagStep
from .steps.github_release import GitHubReleaseStep
from .steps.pypi_publish import PublishPyPiStep
from .steps.s3 import UploadS3Step


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Command-line params")
    parser.add_argument(
        "--mode",
        help="What to do with the package",
        choices=["build", "install", "dev", "reinstall", "uninstall"],
        default="reinstall",
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
    parser.add_argument("--s3-bucket", default=None)
    parser.add_argument("--s3-prefix", default=None)
    parser.add_argument("--git-tag-template", default=None)
    parser.add_argument("--git-remote", default=None)
    parser.add_argument("--git-branch", default=None)
    parser.add_argument("--release-notes-path", default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    project_dir = resolve_project_dir(args.project_dir)
    cli_overrides = {
        key: value
        for key, value in {
            "wheel_glob": args.wheel_glob,
            "s3_bucket": args.s3_bucket,
            "s3_prefix": args.s3_prefix,
            "git_tag_template": args.git_tag_template,
            "git_remote": args.git_remote,
            "git_branch": args.git_branch,
            "release_notes_path": args.release_notes_path,
        }.items()
        if value is not None
    }
    config = load_config(project_dir, cli_overrides)

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
        steps = []
        if args.upload_s3:
            steps.append(UploadS3Step(config))
        if args.create_release:
            steps.append(GitTagStep(config))
            steps.append(GitHubReleaseStep(config))
        if args.publish_pypi:
            steps.append(PublishPyPiStep(config))
        if steps:
            run_release_pipeline(steps)

    return 0
