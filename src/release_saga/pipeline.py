"""Saga-style release pipeline orchestration."""

from __future__ import annotations

import sys
from subprocess import CalledProcessError

from release_saga.steps.base import ReleaseStep


def _log(message: str):
    """Write a release pipeline log message to standard error.

    :param message: Human-readable message to emit.
    """
    print(f"[release] {message}", file=sys.stderr)


def _rollback(steps: list[ReleaseStep]):
    """Attempt best-effort rollback for the supplied release steps.

    :param steps: Steps to roll back in the order they should be attempted.
    """
    for step in steps:
        _log(f"Rolling back: {step.name}")
        try:
            step.rollback()
        except Exception as exc:
            _log(
                f"WARNING: rollback of '{step.name}' also failed ({exc}). "
                "Manual cleanup is required for this step."
            )


def run_release_pipeline(steps: list[ReleaseStep]):
    """Run release steps in order with Saga-style rollback on failure.

    :param steps: Release steps to check and execute sequentially.
    :raises SystemExit: If a check, execution, or rollback-triggering failure occurs.
    """
    completed: list[ReleaseStep] = []
    for step in steps:
        _log(f"Checking availability: {step.name}")
        try:
            reason = step.check()
        except Exception as exc:
            _log(f"ERROR: '{step.name}' availability check failed: {exc}")
            _rollback(list(reversed(completed)))
            raise SystemExit(1) from exc
        if reason is not None:
            _log(f"ERROR: '{step.name}' is not available: {reason}")
            _rollback(list(reversed(completed)))
            raise SystemExit(1)

        _log(f"Running: {step.name}")
        try:
            step.execute()
        except CalledProcessError as exc:
            _log(f"ERROR: '{step.name}' failed (command exited {exc.returncode}): {exc}")
            _rollback([step, *reversed(completed)])
            raise SystemExit(1) from exc
        except Exception as exc:
            _log(f"ERROR: '{step.name}' failed: {exc}")
            _rollback([step, *reversed(completed)])
            raise SystemExit(1) from exc
        else:
            _log(f"Completed: {step.name}")
            completed.append(step)

    _log(f"All {len(steps)} step(s) completed successfully")
