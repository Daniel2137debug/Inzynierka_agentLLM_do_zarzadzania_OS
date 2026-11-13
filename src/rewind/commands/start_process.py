from rewind.commands.base import BaseCommand
from rewind.executor.runner import run_powershell
from rewind.schemas.tools import StartProcess


def process_start_time(pid: int) -> str:
    """When the process with this PID started, or an empty text if none is running - a PID alone can be reused."""
    _, output = run_powershell(f"(Get-Process -Id {pid} -ErrorAction SilentlyContinue).StartTime.Ticks")
    return output


def close_process(pid: int) -> None:
    """Ask the program to close, like its X button, so it can offer to save; stop it at once only if it has no window."""
    _, window = run_powershell(f"(Get-Process -Id {pid}).MainWindowHandle")
    if window == "0":
        run_powershell(f"Stop-Process -Id {pid}")
    else:
        run_powershell(f"(Get-Process -Id {pid}).CloseMainWindow(); Wait-Process -Id {pid} -Timeout 3")

class StartProcessCommand(BaseCommand):
    """Start a program; undo closes it again, if it is still the same process."""

    arguments: StartProcess
    undo_note = "Undo asks the program to close, like its X button; a program with no window is stopped at once."

    def execute(self) -> tuple[bool, str]:
        """Start the program and remember its PID and start time, if it is still running."""
        program = self.arguments.program
        safe_program = program.replace("'", "''")
        success, output = run_powershell(f"(Start-Process -FilePath '{safe_program}' -PassThru).Id")
        if not success:
            return False, f"Could not start {program} - check that it is installed, or give its full path."

        pid = int(output)
        start_time = process_start_time(pid)
        if not start_time:
            return True, f"Started {program}, but its process ended at once - it may have handed over to another one, so /undo cannot close it."

        self.undo_payload = {"pid": pid, "start_time": start_time}
        return True, f"Started {program} (process {pid})."

    def undo(self) -> tuple[bool, str]:
        """Close the program we started, if it is still running under the same PID and start time."""
        program = self.arguments.program
        if not self.undo_payload:
            return True, f"{program} handed over to another process when it started - there is nothing rewind can close."
        
        pid = self.undo_payload["pid"]

        if process_start_time(pid) != self.undo_payload["start_time"]:
            return True, f"{program} (process {pid}) is no longer running - there is nothing to close."

        close_process(pid)
        if process_start_time(pid) == self.undo_payload["start_time"]:
            return False, f"{program} did not close - it may be asking to save something. Close it yourself, then /undo again."

        return True, f"Closed {program}."
