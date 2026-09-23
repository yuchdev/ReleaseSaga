"""Command-line interface helpers for ReleaseSaga."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

from release_saga.config import ReleaseConfig, load_config, resolve_project_dir
from release_saga.history import RunHistory, step_id
from release_saga.package_ops import (
    build_wheel,
    cleanup_old_wheels,
    install_wheel,
    install_wheel_devmode,
    sanity_check,
    uninstall_wheel,
)
from release_saga.pipeline import clean_release_run, run_release_pipeline
from release_saga.plugins import PluginLoadError, load_plugin_steps
from release_saga.steps.base import ReleaseStep
from release_saga.steps.git_tag import GitTagStep
from release_saga.steps.github_release import GitHubReleaseStep
from release_saga.steps.pypi_publish import PublishPyPiStep
from release_saga.steps.s3 import UploadS3Step
from release_saga.version_ops import set_release_version


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the ``release-saga`` CLI.

    :returns: Configured parser containing all supported command-line options.
    """
    parser = argparse.ArgumentParser(description="Command-line params")
    parser.add_argument(
        "--mode",
        help="What to do with the package",
        choices=["build", "install", "dev", "reinstall", "uninstall", "set-version", "clean"],
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
    parser.add_argument(
        "--no-plugins",
        help="Disable loading plugin steps (both [tool.release-saga] extra_steps and entry points)",
        action="store_true",
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
    plugin_steps: Optional[list[ReleaseStep]] = None,
) -> list[ReleaseStep]:
    """Assemble the built-in release steps selected by CLI flags.

    :param config: Resolved release configuration for the target project.
    :param upload_s3: Whether to include the S3 upload step.
    :param create_release: Whether to include git tagging and GitHub release creation.
    :param publish_pypi: Whether to include the PyPI publishing step.
    :param plugin_steps: Plugin-provided steps (see `release_saga.plugins`) to run after the
        built-in S3/git/GitHub steps but before the irreversible PyPI publish step.
    :returns: Release step instances in the order they must run.
    """
    steps: list[ReleaseStep] = []
    if upload_s3:
        steps.append(UploadS3Step(config))
    if create_release:
        steps.append(GitTagStep(config))
        steps.append(GitHubReleaseStep(config))
    if plugin_steps:
        steps.extend(plugin_steps)
    if publish_pypi:
        steps.append(PublishPyPiStep(config))
    return steps


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the ReleaseSaga command-line application.

    :param argv: Optional argument list to parse instead of ``sys.argv[1:]``.
    :raises SystemExit: If argument validation fails or a release operation aborts.
    :returns: Exit status code for a successfully handled command.
    """
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

    if args.mode == "clean":
        history = RunHistory.latest_incomplete(config)
        if history is None:
            print(f"No incomplete release run found for {config.package_name_dash} {config.version}")
            return 0
        built_in_types = {
            f"{UploadS3Step.__module__}:{UploadS3Step.__qualname__}",
            f"{GitTagStep.__module__}:{GitTagStep.__qualname__}",
            f"{GitHubReleaseStep.__module__}:{GitHubReleaseStep.__qualname__}",
            f"{PublishPyPiStep.__module__}:{PublishPyPiStep.__qualname__}",
        }
        records = [
            record
            for record in history.data["steps"]
            if record.get("status") in {"completed", "rollback_failed"}
        ]
        needs_plugins = any(record.get("id") not in built_in_types for record in records)
        plugin_steps: list[ReleaseStep] = []
        if needs_plugins and not args.no_plugins:
            try:
                plugin_steps = load_plugin_steps(config)
            except PluginLoadError as exc:
                parser.error(str(exc))
        candidates: dict[str, list[ReleaseStep]] = {}
        for step in plugin_steps:
            candidates.setdefault(step_id(step), []).append(step)
        recovery_steps: list[ReleaseStep] = []
        for record in records:
            identifier = record.get("id")
            recovery_data = record.get("recovery_data", {})
            if identifier == f"{UploadS3Step.__module__}:{UploadS3Step.__qualname__}":
                key = str(recovery_data.get("key", "release.whl"))
                step = UploadS3Step(config, Path(key).name)
            elif identifier == f"{GitTagStep.__module__}:{GitTagStep.__qualname__}":
                step = GitTagStep(config)
            elif identifier == f"{GitHubReleaseStep.__module__}:{GitHubReleaseStep.__qualname__}":
                step = GitHubReleaseStep(config)
            elif identifier == f"{PublishPyPiStep.__module__}:{PublishPyPiStep.__qualname__}":
                step = PublishPyPiStep(config)
            else:
                matching = candidates.get(identifier, [])
                if not matching:
                    parser.error(f"Cannot reconstruct recorded release step '{record.get('name')}'")
                step = matching.pop(0)
            recovery_steps.append(step)
        clean_release_run(recovery_steps, history)
        print(f"Cleaned interrupted release run {history.data['run_id']}")
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
        plugin_steps: list[ReleaseStep] = []
        if not args.no_plugins:
            try:
                plugin_steps = load_plugin_steps(config)
            except PluginLoadError as exc:
                parser.error(str(exc))

        steps = build_release_steps(
            config,
            upload_s3=args.upload_s3,
            create_release=args.create_release,
            publish_pypi=args.publish_pypi,
            plugin_steps=plugin_steps,
        )
        if steps:
            run_release_pipeline(steps, config)

    return 0
