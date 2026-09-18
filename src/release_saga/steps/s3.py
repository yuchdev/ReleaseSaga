"""Amazon S3 upload step for the release pipeline."""

from __future__ import annotations

from pathlib import Path
from subprocess import run

from release_saga.config import ReleaseConfig
from release_saga.package_ops import command_ok, executable_exists, resolve_wheel_path
from release_saga.steps.base import ReleaseStep


class UploadS3Step(ReleaseStep):
    """Upload a built wheel to an S3 bucket.

    :param config: Resolved release configuration for the target project.
    :param wheel_path: Optional wheel path to upload instead of resolving one from the config.
    """

    #: Human-readable step name used in pipeline logs.
    name = "upload wheel to S3"

    def __init__(self, config: ReleaseConfig, wheel_path: Path | None = None):
        """Initialize the S3 upload step.

        :param config: Resolved release configuration for the target project.
        :param wheel_path: Optional wheel path to upload instead of resolving one from the config.
        """
        self.config = config
        self.wheel_path = wheel_path or resolve_wheel_path(config)

    def _prefix(self) -> str:
        """Render the configured S3 key prefix.

        :returns: Prefix string with format placeholders expanded.
        """
        return self.config.s3_prefix.format(
            package_name=self.config.package_name,
            package_name_dash=self.config.package_name_dash,
        )

    def _key(self) -> str:
        """Build the full S3 object key for the wheel artifact.

        :returns: Object key combining the rendered prefix and wheel filename.
        """
        prefix = self._prefix().lstrip("/")
        if not prefix:
            return self.wheel_path.name
        normalized_prefix = prefix if prefix.endswith("/") else f"{prefix}/"
        return f"{normalized_prefix}{self.wheel_path.name}"

    def check(self) -> str | None:
        """Check that the S3 upload can proceed safely.

        :returns: ``None`` when upload can proceed, otherwise a blocking reason.
        """
        if self.config.s3_bucket is None:
            return "no s3_bucket configured (set [tool.release-saga].s3_bucket or --s3-bucket)"
        if not executable_exists("aws"):
            return "awscli not installed"
        if not command_ok(["aws", "sts", "get-caller-identity"]):
            return "aws credentials are not configured or not valid"
        if command_ok(
            [
                "aws",
                "s3api",
                "head-object",
                "--bucket",
                self.config.s3_bucket,
                "--key",
                self._key(),
            ],
            cwd=self.config.project_dir,
        ):
            return f"S3 object '{self._key()}' already exists in bucket '{self.config.s3_bucket}'"
        return None

    def execute(self):
        """Upload the wheel artifact to S3.

        :raises CalledProcessError: If the AWS CLI upload command fails.
        """
        run(
            [
                "aws",
                "s3",
                "cp",
                str(self.wheel_path),
                f"s3://{self.config.s3_bucket}/{self._key()}",
                "--acl",
                "public-read",
            ],
            check=True,
            cwd=self.config.project_dir,
        )

    def rollback(self):
        """Delete the S3 object uploaded by this run.

        :raises CalledProcessError: If the AWS CLI delete command fails.
        """
        run(
            ["aws", "s3", "rm", f"s3://{self.config.s3_bucket}/{self._key()}"],
            check=True,
            cwd=self.config.project_dir,
        )
