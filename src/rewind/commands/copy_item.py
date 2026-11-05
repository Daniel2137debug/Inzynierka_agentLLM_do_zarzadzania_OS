import os

from rewind.commands.base import BaseCommand
from rewind.commands.delete_item import quarantine_folder
from rewind.executor.runner import run_powershell
from rewind.schemas.tools import CopyItem


class CopyItemCommand(BaseCommand):
    """Copy an item to a new full path; undo moves the copy to quarantine instead of destroying it."""

    arguments: CopyItem

    def execute(self) -> tuple[bool, str]:
        """Copy the item and remember the copy's file ID, so undo can tell it is still the same copy."""
        path = self.arguments.path
        destination = self.arguments.destination
        parent = os.path.dirname(destination)

        if not os.path.exists(path):
            return False, f"{path} does not exist - nothing to copy."
        if os.path.exists(destination):
            return False, f"{destination} already exists - give the copy's full path, including its name."
        if not os.path.isdir(parent):
            return False, f"{parent} does not exist - there is nowhere to put the copy."
        if os.path.normcase(destination).startswith(os.path.normcase(path) + os.sep):
            return False, f"{destination} is inside {path} - a folder cannot be copied into itself."

        safe_path = path.replace("'", "''")
        safe_destination = destination.replace("'", "''")
        success, output = run_powershell(f"Copy-Item -LiteralPath '{safe_path}' -Destination '{safe_destination}' -Recurse")
        if not success:
            return False, output
        if not os.path.exists(destination):
            return False, f"Copy-Item reported success, but {destination} does not exist."

        stat = os.stat(destination)
        self.undo_payload = {"file_id": stat.st_ino, "volume_id": stat.st_dev}
        return True, f"Copied {path} to {destination}."

    def undo(self) -> tuple[bool, str]:
        """Move the copy to its record's quarantine folder - it may hold changes made after the copy."""
        destination = self.arguments.destination
        if not os.path.exists(destination):
            return True, f"{destination} no longer exists - there is nothing left to undo."
        stat = os.stat(destination)
        if (stat.st_ino, stat.st_dev) != (self.undo_payload["file_id"], self.undo_payload["volume_id"]):
            return False, f"{destination} is a different item now - it was replaced after the copy."

        folder = quarantine_folder(destination, self.record_id)
        target = os.path.join(folder, os.path.basename(destination))
        os.makedirs(folder, exist_ok=True)

        safe_destination = destination.replace("'", "''")
        safe_target = target.replace("'", "''")
        success, output = run_powershell(f"Move-Item -LiteralPath '{safe_destination}' -Destination '{safe_target}'")
        if not success:
            if not os.listdir(folder):
                os.rmdir(folder)
            return False, output
        if os.path.exists(destination) or not os.path.exists(target):
            return False, f"Move-Item reported success, but {destination} did not reach the quarantine."
        return True, f"Moved the copy {destination} to quarantine: {target}"