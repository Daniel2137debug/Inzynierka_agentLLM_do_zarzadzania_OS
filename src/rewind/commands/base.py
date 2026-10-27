from abc import ABC, abstractmethod

from pydantic import BaseModel


class BaseCommand(ABC):
    """One operation the agent can run and take back - the Command pattern behind /undo."""

    def __init__(self, arguments: BaseModel, undo_payload: dict | None = None) -> None:
        self.arguments = arguments
        # What undo() needs besides the arguments, e.g. rename's file ID. execute() fills it in.
        self.undo_payload = undo_payload or {}

    @abstractmethod
    def execute(self) -> tuple[bool, str]:
        """Run the operation and report whether it really happened."""

    @abstractmethod
    def undo(self) -> tuple[bool, str]:
        """Restore the state from before execute(), or refuse and say what changed."""