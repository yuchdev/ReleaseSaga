"""Saga-style release pipeline orchestration."""

from __future__ import annotations

import sys
from subprocess import CalledProcessError
from typing import Optional

from release_saga.config import ReleaseConfig
from release_saga.history import RunHistory, step_id
from release_saga.steps.base import ReleaseStep


def _log(message: str):
    """Write a release pipeline log message to standard error.

    :param message: Human-readable message to emit.
    """
    print(f"[release] {message}", file=sys.stderr)


def _rollback(steps: list[tuple[int, ReleaseStep]], history: Optional[RunHistory] = None) -> bool:
    """Attempt best-effort rollback for the supplied release steps.

    :param steps: Steps to roll back in the order they should be attempted.
    """
    succeeded = True
    for index, step in steps:
        _log(f"Rolling back: {step.name}")
        try:
            step.rollback()
        except Exception as exc:
            succeeded = False
            if history is not None:
                history.set_step_status(index, "rollback_failed")
            _log(
                f"WARNING: rollback of '{step.name}' also failed ({exc}). "
                "Manual cleanup is required for this step."
            )
        else:
            if history is not None:
                history.set_step_status(index, "rolled_back")
    return succeeded


def run_release_pipeline(steps: list[ReleaseStep], config: Optional[ReleaseConfig] = None):
    """Run release steps in order with Saga-style rollback on failure.

    :param steps: Release steps to check and execute sequentially.
    :raises SystemExit: If a check, execution, or rollback-triggering failure occurs.
    """
    if config is None and steps:
        inferred_config = getattr(steps[0], "config", None)
        if isinstance(inferred_config, ReleaseConfig):
            config = inferred_config
    history = RunHistory.create(config, steps) if config is not None else None
    completed: list[tuple[int, ReleaseStep]] = []
    for index, step in enumerate(steps):
        _log(f"Checking availability: {step.name}")
        try:
            reason = step.check()
        except Exception as exc:
            _log(f"ERROR: '{step.name}' availability check failed: {exc}")
            rolled_back = _rollback(list(reversed(completed)), history)
            if history is not None:
                history.set_status("rolled_back" if rolled_back else "rollback_failed")
            raise SystemExit(1) from exc
        if reason is not None:
            _log(f"ERROR: '{step.name}' is not available: {reason}")
            rolled_back = _rollback(list(reversed(completed)), history)
            if history is not None:
                history.set_status("rolled_back" if rolled_back else "rollback_failed")
            raise SystemExit(1)

        _log(f"Running: {step.name}")
        if history is not None:
            history.set_step_status(index, "in_progress")
        try:
            step.execute()
        except CalledProcessError as exc:
            _log(f"ERROR: '{step.name}' failed (command exited {exc.returncode}): {exc}")
            rolled_back = _rollback([(index, step), *reversed(completed)], history)
            if history is not None:
                history.set_status("rolled_back" if rolled_back else "rollback_failed")
            raise SystemExit(1) from exc
        except Exception as exc:
            _log(f"ERROR: '{step.name}' failed: {exc}")
            rolled_back = _rollback([(index, step), *reversed(completed)], history)
            if history is not None:
                history.set_status("rolled_back" if rolled_back else "rollback_failed")
            raise SystemExit(1) from exc
        else:
            _log(f"Completed: {step.name}")
            completed.append((index, step))
            if history is not None:
                history.set_step_status(index, "completed", step.recovery_data())

    if history is not None:
        history.set_status("completed")
    _log(f"All {len(steps)} step(s) completed successfully")


def clean_release_run(steps: list[ReleaseStep], history: RunHistory):
    """Roll back completed work from an interrupted run."""
    records = [
        (index, record)
        for index, record in enumerate(history.data["steps"])
        if record.get("status") in {"completed", "rollback_failed"}
    ]
    if len(steps) != len(records) or any(
        step_id(step) != record.get("id")
        for step, (_, record) in zip(steps, records, strict=True)
    ):
        raise RuntimeError("Recorded release steps cannot be reconstructed from the current configuration")

    rollback_steps: list[tuple[int, ReleaseStep]] = []
    for step, (index, record) in zip(steps, records, strict=True):
        step.prepare_rollback(record.get("recovery_data", {}))
        rollback_steps.append((index, step))

    rolled_back = _rollback(list(reversed(rollback_steps)), history)
    history.set_status("rolled_back" if rolled_back else "rollback_failed")
    if not rolled_back:
        raise SystemExit(1)
