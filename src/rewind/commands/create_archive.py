import os

from rewind.commands.base import BaseCommand
from rewind.commands.delete_item import quarantine_folder
from rewind.executor.runner import run_powershell
from rewind.schemas.tools import CreateArchive


class CreateArchiveCommand(BaseCommand):
    """Pack an item into a new .zip archive; undo moves the archive to quarantine instead of destroying it."""

    arguments: CreateArchive

    def execute(self) -> tuple[bool, str]:
        """Create the archive and remember its file ID, so undo can tell it is still the same archive."""
        path = self.arguments.path
        destination = self.arguments.destination
        parent = os.path.dirname(destination)

        if not os.path.exists(path):
            return False, f"{path} does not exist - nothing to pack."
        if not destination.lower().endswith(".zip"):
            return False, f"{destination} must end with .zip."
        if os.path.exists(destination):
            return False, f"{destination} already exists - give a new archive path."
        if not os.path.isdir(parent):
            return False, f"{parent} does not exist - there is nowhere to put the archive."

        safe_path = path.replace("'", "''")
        safe_destination = destination.replace("'", "''")
        success, output = run_powershell(f"Compress-Archive -LiteralPath '{safe_path}' -DestinationPath '{safe_destination}'")
        if not success:
            return False, output
        if not os.path.exists(destination):
            return False, f"Compress-Archive reported success, but {destination} does not exist."

        stat = os.stat(destination)
        self.undo_payload = {"file_id": stat.st_ino, "volume_id": stat.st_dev}
        return True, f"Packed {path} into {destination}."

    def undo(self) -> tuple[bool, str]:
        """Move the archive to its record's quarantine folder, if it is still the same archive."""
        destination = self.arguments.destination
        if not os.path.exists(destination):
            return True, f"{destination} no longer exists - there is nothing left to undo."
        stat = os.stat(destination)
        if (stat.st_ino, stat.st_dev) != (self.undo_payload["file_id"], self.undo_payload["volume_id"]):
            return False, f"{destination} is a different item now - it was replaced after it was created."

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
        return True, f"Moved the archive {destination} to quarantine: {target}"