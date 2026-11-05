import os

from rewind.commands.base import BaseCommand
from rewind.executor.runner import run_powershell
from rewind.schemas.tools import MoveItem


class MoveItemCommand(BaseCommand):
    """Move an item to a new full path; undo moves it back, if it is still the same item."""

    arguments: MoveItem

    def execute(self) -> tuple[bool, str]:
        """Move the item and remember its file ID where it landed - a move to another drive changes it."""
        path = self.arguments.path
        destination = self.arguments.destination
        parent = os.path.dirname(destination)

        if not os.path.exists(path):
            return False, f"{path} does not exist - nothing to move."
        if os.path.exists(destination):
            return False, f"{destination} already exists - give the item's full new path, including its name."
        if not os.path.isdir(parent):
            return False, f"{parent} does not exist - there is nowhere to move {path} to."

        safe_path = path.replace("'", "''")
        safe_destination = destination.replace("'", "''")
        success, output = run_powershell(f"Move-Item -LiteralPath '{safe_path}' -Destination '{safe_destination}'")
        if not success:
            return False, output
        if os.path.exists(path) or not os.path.exists(destination):
            return False, f"Move-Item reported success, but {path} did not arrive at {destination}."

        stat = os.stat(destination)
        self.undo_payload = {"file_id": stat.st_ino, "volume_id": stat.st_dev}
        return True, f"Moved {path} to {destination}."

    def undo(self) -> tuple[bool, str]:
        """Move the item back, if it is still the same item and its old place is free."""
        path = self.arguments.path
        destination = self.arguments.destination
        parent = os.path.dirname(path)

        if not os.path.exists(destination):
            return True, f"{destination} no longer exists - there is nothing left to move back."
        stat = os.stat(destination)
        if (stat.st_ino, stat.st_dev) != (self.undo_payload["file_id"], self.undo_payload["volume_id"]):
            return False, f"{destination} is a different item now - it was replaced after the move."
        if os.path.exists(path):
            return False, f"{path} is taken again - undo would overwrite it."
        if not os.path.isdir(parent):
            return False, f"{parent} no longer exists - there is nowhere to move {destination} back to."

        safe_destination = destination.replace("'", "''")
        safe_path = path.replace("'", "''")
        success, output = run_powershell(f"Move-Item -LiteralPath '{safe_destination}' -Destination '{safe_path}'")
        if not success:
            return False, output
        if not os.path.exists(path):
            return False, f"Move-Item reported success, but {path} does not exist."
        return True, f"Moved {destination} back to {path}."