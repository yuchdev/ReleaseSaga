"""Persistent release run history used for interrupted-run recovery."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Optional
from urllib.parse import quote
from uuid import uuid4

from release_saga.config import ReleaseConfig
from release_saga.steps.base import ReleaseStep


def _now() -> str:
    return datetime.now(UTC).isoformat()


def step_id(step: ReleaseStep) -> str:
    """Return the stable identifier persisted for a release step."""
    step_type = type(step)
    return f"{step_type.__module__}:{step_type.__qualname__}"


def _data_home() -> Path:
    configured = os.environ.get("XDG_DATA_HOME")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".local" / "share"


def _history_dir(config: ReleaseConfig) -> Path:
    package = quote(config.package_name_dash, safe="")
    version = quote(config.version, safe="")
    return _data_home() / "release-saga" / package / version


class RunHistory:
    """A single persisted release run record."""

    def __init__(self, path: Path, data: dict[str, Any]):
        self.path = path
        self.data = data

    @classmethod
    def create(cls, config: ReleaseConfig, steps: list[ReleaseStep]) -> RunHistory:
        """Create and persist a new in-progress run."""
        run_id = uuid4().hex
        path = _history_dir(config) / f"{run_id}.json"
        history = cls(
            path,
            {
                "run_id": run_id,
                "package_name": config.package_name_dash,
                "version": config.version,
                "started_at": _now(),
                "status": "in_progress",
                "steps": [
                    {
                        "id": step_id(step),
                        "name": step.name,
                        "status": "pending",
                        "recovery_data": step.recovery_data(),
                    }
                    for step in steps
                ],
            },
        )
        history.save()
        return history

    @classmethod
    def latest_incomplete(cls, config: ReleaseConfig) -> Optional[RunHistory]:
        """Load the newest interrupted or incompletely rolled-back run."""
        directory = _history_dir(config)
        if not directory.is_dir():
            return None
        candidates: list[RunHistory] = []
        for path in directory.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if (
                isinstance(data, dict)
                and data.get("package_name") == config.package_name_dash
                and data.get("version") == config.version
                and data.get("status") in {"in_progress", "rollback_failed"}
                and isinstance(data.get("steps"), list)
            ):
                candidates.append(cls(path, data))
        if not candidates:
            return None
        return max(candidates, key=lambda item: str(item.data.get("started_at", "")))

    def save(self):
        """Atomically persist the current run record."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w",
            dir=self.path.parent,
            prefix=f".{self.path.name}.",
            delete=False,
            encoding="utf-8",
        ) as handle:
            json.dump(self.data, handle, indent=2)
            handle.write("\n")
            temporary_path = Path(handle.name)
        try:
            os.replace(temporary_path, self.path)
        finally:
            temporary_path.unlink(missing_ok=True)

    def set_step_status(self, index: int, status: str):
        """Update one step and persist the record."""
        step = self.data["steps"][index]
        step["status"] = status
        step[f"{status}_at"] = _now()
        self.save()

    def set_status(self, status: str):
        """Update the overall run status and persist the record."""
        self.data["status"] = status
        self.data[f"{status}_at"] = _now()
        self.save()
