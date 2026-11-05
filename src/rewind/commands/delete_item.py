import os

from rewind.commands.base import BaseCommand
from rewind.executor.runner import run_powershell
from rewind.schemas.tools import DeleteItem


def quarantine_folder(path: str, record_id: int) -> str:
    """The record's quarantine folder, on the item's own drive - a move within one drive is instant and cannot stop halfway."""
    drive = os.path.splitdrive(path)[0]
    local_app_data = os.getenv("LOCALAPPDATA")
    if drive.lower() == os.path.splitdrive(local_app_data)[0].lower():
        root = os.path.join(local_app_data, "rewind", "quarantine")
    else:
        root = os.path.join(drive + "\\", "rewind-quarantine")
    return os.path.join(root, str(record_id))


class DeleteItemCommand(BaseCommand):
    """Delete a file or directory by moving it to quarantine; undo moves it back."""

    arguments: DeleteItem

    def execute(self) -> tuple[bool, str]:
        """Move the item to its record's quarantine folder and check that it really got there."""
        path = self.arguments.path
        if not os.path.exists(path):
            return False, f"{path} does not exist - nothing to delete."
        folder = quarantine_folder(path, self.record_id)
        target = os.path.join(folder, os.path.basename(path))
        os.makedirs(folder, exist_ok=True)

        safe_path = path.replace("'", "''")
        safe_target = target.replace("'", "''")
        success, output = run_powershell(f"Move-Item -LiteralPath '{safe_path}' -Destination '{safe_target}'")
        if not success:
            if not os.listdir(folder):
                os.rmdir(folder)
            return False, output
        if os.path.exists(path) or not os.path.exists(target):
            return False, f"Move-Item reported success, but {path} did not reach the quarantine."
        return True, f"Deleted {path} - kept in quarantine, /undo restores it."

    def undo(self) -> tuple[bool, str]:
        """Move the item back from quarantine, unless its old place is taken or gone."""
        path = self.arguments.path
        folder = quarantine_folder(path, self.record_id)
        target = os.path.join(folder, os.path.basename(path))
        parent = os.path.dirname(path)

        if not os.path.exists(target):
            return True, f"{target} is gone - there is nothing left to restore."
        if os.path.exists(path):
            return False, f"{path} is taken again - undo would overwrite it."
        if not os.path.isdir(parent):
            return False, f"{parent} no longer exists - there is nowhere to restore {path} to."

        safe_target = target.replace("'", "''")
        safe_path = path.replace("'", "''")
        success, output = run_powershell(f"Move-Item -LiteralPath '{safe_target}' -Destination '{safe_path}'")
        if not success:
            return False, output
        if not os.path.exists(path):
            return False, f"Move-Item reported success, but {path} does not exist."

        if not os.listdir(folder):
            os.rmdir(folder)
        return True, f"Restored {path} from quarantine."