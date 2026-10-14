from rewind.executor.runner import run_powershell
from rewind.schemas.tools import CreateItem



class CreateItemCommand:
    """Create an empty file or directory; undo removes it again."""

    def __init__(self, arguments: CreateItem) -> None:
        self.arguments = arguments

    def execute(self) -> tuple[bool, str]:
        """Create the item and report PowerShell's verdict."""
        safe_path = self.arguments.path.replace("'", "''")
        item_type = "Directory" if self.arguments.kind == "directory" else "File"
        ps_command = f"New-Item -ItemType {item_type} -Path '{safe_path}'"
        return run_powershell(ps_command)