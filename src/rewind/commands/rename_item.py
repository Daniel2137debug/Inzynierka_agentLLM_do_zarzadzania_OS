import os

from rewind.commands.base import BaseCommand
from rewind.executor.runner import run_powershell
from rewind.schemas.tools import RenameItem


class RenameItemCommand(BaseCommand):
    """Rename an item in place; undo gives it its old name back."""

    arguments: RenameItem

    def execute(self) -> tuple[bool, str]:
        """Rename the item and remember its file ID, so undo can tell it is still the same item."""
        #safe_path and safe_name are used to escape single quotes in the path and new name for PowerShell
        path = self.arguments.path
        new_path = os.path.join(os.path.dirname(path), self.arguments.new_name)
        safe_path = path.replace("'", "''")
        safe_name = self.arguments.new_name.replace("'", "''")

        success, output = run_powershell(f"Rename-Item -LiteralPath '{safe_path}' -NewName '{safe_name}'")
        if not success:
            return False, output
        if not os.path.exists(new_path):
            return False, f"Rename-Item reported success, but {new_path} does not exist."

        
        stat = os.stat(new_path)
        self.undo_payload = {"file_id": stat.st_ino, "volume_id": stat.st_dev}
        return True, f"Renamed {path} to {self.arguments.new_name}."

    def undo(self) -> tuple[bool, str]:
        """Give the item its old name back, if it is still the same item and the old name is free."""
        #undo usually works after reset so we need to define the path and new_path again
        path = self.arguments.path
        new_path = os.path.join(os.path.dirname(path), self.arguments.new_name)
        old_name = os.path.basename(path)

        if not os.path.exists(new_path):
            return True, f"{new_path} no longer exists - there is nothing left to rename back."
        stat = os.stat(new_path)
        if (stat.st_ino, stat.st_dev) != (self.undo_payload["file_id"], self.undo_payload["volume_id"]):
            return False, f"{new_path} is a different item now - it was replaced after the rename."
        if os.path.exists(path):
            return False, f"{path} is taken again - undo would overwrite it."

        safe_new_path = new_path.replace("'", "''")
        safe_old_name = old_name.replace("'", "''")
        success, output = run_powershell(f"Rename-Item -LiteralPath '{safe_new_path}' -NewName '{safe_old_name}'")
        if not success:
            return False, output
        if not os.path.exists(path):
            return False, f"Rename-Item reported success, but {path} does not exist."

        return True, f"Renamed {self.arguments.new_name} back to {old_name}."