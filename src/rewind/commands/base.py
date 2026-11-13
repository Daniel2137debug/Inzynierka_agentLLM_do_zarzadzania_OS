from abc import ABC, abstractmethod

from pydantic import BaseModel


class BaseCommand(ABC):
    """One operation the agent can run and take back - the Command pattern behind /undo."""

    # False for an operation that cannot be reversed: the REPL warns before approval and /undo skips its records.
    can_undo = True
    # A line shown before "Undo? (y/n)" when undo does something the user may not expect; empty for most commands.
    undo_note = ""

    def __init__(self, arguments: BaseModel, record_id: int, undo_payload: dict | None = None) -> None:
        self.arguments = arguments
        
        self.record_id = record_id
        
        self.undo_payload = undo_payload or {}

    @abstractmethod
    def execute(self) -> tuple[bool, str]:
        """Run the operation and report whether it really happened."""

    @abstractmethod
    def undo(self) -> tuple[bool, str]:
        """Restore the state from before execute(), or refuse and say what changed."""