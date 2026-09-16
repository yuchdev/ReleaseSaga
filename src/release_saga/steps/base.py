from __future__ import annotations

from abc import ABC, abstractmethod


class ReleaseStep(ABC):
    """One stage of a reversible release pipeline."""

    name: str = "release step"

    def check(self) -> str | None:
        """Return None when the step can run, otherwise a reason it cannot."""
        return None

    @abstractmethod
    def execute(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        raise NotImplementedError
