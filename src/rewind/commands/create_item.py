import os

from rewind.commands.base import BaseCommand
from rewind.executor.runner import run_powershell
from rewind.schemas.tools import CreateItem


class CreateItemCommand(BaseCommand):
    """Create an empty file or directory; undo removes it again."""

    arguments: CreateItem

    def execute(self) -> tuple[bool, str]:
        """Create the item and check that it really exists."""
        path = self.arguments.path
        safe_path = path.replace("'", "''")
        item_type = "Directory" if self.arguments.kind == "directory" else "File"
        ps_command = f"New-Item -ItemType {item_type} -Path '{safe_path}'"
        success, output = run_powershell(ps_command)
        if not success:
            return False, output
        if not os.path.exists(path):
            return False, f"New-Item reported success, but {path} does not exist."
        return True, f"Created {path}."

    def undo(self) -> tuple[bool, str]:
        """Remove the created item again, but only if nothing was added to it since."""
        path = self.arguments.path
        if not os.path.exists(path):
            return True, f"{path} no longer exists - nothing to remove."
        if self.arguments.kind == "directory":
            if not os.path.isdir(path):
                return False, f"{path} is no longer a directory - something else took its place."
            elif os.listdir(path) != []:
                return False, f"{path} is not empty - undo would delete files added after it was created."
        else:
            if not os.path.isfile(path):
                return False, f"{path} is no longer a file - something else took its place."
            elif os.path.getsize(path) > 0:
                return False, f"{path} has content now - undo would delete it."
        safe_path = self.arguments.path.replace("'", "''")
        success, output = run_powershell(f"Remove-Item -LiteralPath '{safe_path}'")
        if not success:
            return False, output
        if os.path.exists(path):
            return False, f"{path} still exists after undo - something went wrong."

        return True, f"Removed {path}."