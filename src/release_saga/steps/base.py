"""Abstract base class for reversible release steps."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ReleaseStep(ABC):
    """One stage of a reversible release pipeline.

    Subclasses implement a preflight ``check()``, the forward ``execute()`` action,
    and a best-effort ``rollback()``.
    """

    #: Human-readable step name used in pipeline logs.
    name: str = "release step"

    def check(self) -> str | None:
        """Validate that the step can run.

        :returns: ``None`` when the step is ready, otherwise a message explaining why it cannot run.
        """
        return None

    def recovery_data(self) -> dict[str, Any]:
        """Return JSON-serializable data needed to reconstruct rollback state."""
        return {}

    def prepare_rollback(self, recovery_data: dict[str, Any]):
        """Restore state needed to roll back work completed in an earlier process."""
        del recovery_data

    @abstractmethod
    def execute(self):
        """Perform the release action for this step.

        :raises NotImplementedError: Always, until implemented by a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def rollback(self):
        """Undo work previously performed by this step when possible.

        :raises NotImplementedError: Always, until implemented by a subclass.
        """
        raise NotImplementedError
