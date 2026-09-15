from __future__ import annotations

import sys
from subprocess import CalledProcessError

from .steps.base import ReleaseStep


def _log(message: str) -> None:
    print(f"[release] {message}", file=sys.stderr)


def _rollback(steps: list[ReleaseStep]) -> None:
    """Best-effort rollback for completed release steps."""
    for step in steps:
        _log(f"Rolling back: {step.name}")
        try:
            step.rollback()
        except Exception as exc:
            _log(
                f"WARNING: rollback of '{step.name}' also failed ({exc}). "
                "Manual cleanup is required for this step."
            )


def run_release_pipeline(steps: list[ReleaseStep]) -> None:
    """Run release steps in order, rolling back on unavailability or failure."""
    completed: list[ReleaseStep] = []
    for step in steps:
        _log(f"Checking availability: {step.name}")
        reason = step.check()
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
