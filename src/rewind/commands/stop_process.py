from rewind.commands.base import BaseCommand
from rewind.executor.runner import run_powershell
from rewind.schemas.tools import StopProcess


def processes_named(name: str) -> list[tuple[int, str]]:
    """Every running process with this name, as (PID, window title) pairs - the title tells the user which is which."""
    if name.lower().endswith(".exe"):
        name = name[:-4]
    safe_name = name.replace("'", "''")
    _, output = run_powershell(f"Get-Process -Name '{safe_name}' -ErrorAction SilentlyContinue | ForEach-Object {{ \"$($_.Id) $($_.MainWindowTitle)\" }}")
    processes = []
    for line in output.splitlines():
        pid, _, title = line.partition(" ")
        processes.append((int(pid), title))
    return processes


def stop_by_pid(pid: int) -> bool:
    """Stop the process at once and report whether it is really gone - exit code 0 is not proof."""
    run_powershell(f"Stop-Process -Id {pid}; Wait-Process -Id {pid} -Timeout 3 -ErrorAction SilentlyContinue")
    _, output = run_powershell(f"Get-Process -Id {pid} -ErrorAction SilentlyContinue")
    return output == ""


class StopProcessCommand(BaseCommand):
    """Stop a running program by name - irreversible, so /undo skips it and the user is warned before approving."""

    can_undo = False
    arguments: StopProcess

    def execute(self) -> tuple[bool, str]:
        """Stop the one process with this name; refuse when the name is ambiguous."""
        name = self.arguments.name
        processes = processes_named(name)

        if not processes:
            return False, f"Nothing to stop - no running program is named {name}. Use the name from Task Manager's Details tab, e.g. winword for Word."

        #this one exists in case of multiple processes like chrome.exe where many tabs simultaneously run, so we dont want to stop all of them bc its a hazard of closing some tabs what we wouldnt want to close
        if len(processes) > 1:
            listing = "\n".join(f" {pid} {title or '(no window)'}" for pid, title in processes) 
            return False, f"{len(processes)} processes are named {name} - rewind never stops more than one. Close the right one yourself:\n{listing}"

        pid, _ = processes[0]

        if not stop_by_pid(pid):
            return False, f"{name} (process {pid}) did not stop."
        return True, f"Stopped {name} (process {pid})."



    def undo(self) -> tuple[bool, str]:
        """Never reached, /undo skips irreversible records - but the Command pattern demands it."""
        return False, f"{self.arguments.name} was stopped - a stopped program cannot be brought back with its work."