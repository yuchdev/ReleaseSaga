from __future__ import annotations

from pathlib import Path
from subprocess import run

from ..config import ReleaseConfig
from ..package_ops import command_ok, executable_exists, resolve_wheel_path
from .base import ReleaseStep


class UploadS3Step(ReleaseStep):
    name = "upload wheel to S3"

    def __init__(self, config: ReleaseConfig, wheel_path: Path | None = None):
        self.config = config
        self.wheel_path = wheel_path or resolve_wheel_path(config)

    def _prefix(self) -> str:
        return self.config.s3_prefix.format(
            package_name=self.config.package_name,
            package_name_dash=self.config.package_name_dash,
        )

    def check(self) -> str | None:
        if self.config.s3_bucket is None:
            return "no s3_bucket configured (set [tool.release-saga].s3_bucket or --s3-bucket)"
        if not executable_exists("aws"):
            return "awscli not installed"
        if not command_ok(["aws", "sts", "get-caller-identity"]):
            return "aws credentials are not configured or not valid"
        return None

    def execute(self) -> None:
        run(
            [
                "aws",
                "s3",
                "cp",
                str(self.wheel_path),
                f"s3://{self.config.s3_bucket}/{self._prefix()}",
                "--acl",
                "public-read",
            ],
            check=True,
            cwd=self.config.project_dir,
        )

    def rollback(self) -> None:
        key = f"{self._prefix()}{self.wheel_path.name}"
        run(
            ["aws", "s3", "rm", f"s3://{self.config.s3_bucket}/{key}"],
            check=True,
            cwd=self.config.project_dir,
        )
