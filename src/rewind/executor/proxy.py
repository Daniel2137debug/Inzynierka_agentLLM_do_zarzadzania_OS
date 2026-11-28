"""The safety gate, called Proxy in the design: blocks a proposed operation that would touch a folder rewind protects - paths only, no disk access."""
import ntpath
import os

from rewind.collision import overlaps, touched_paths


def protected_folders(path: str) -> list[str]:
    """Folders no operation may touch: rewind's journal and quarantine, the quarantine on the path's own drive, and Windows' own folders."""
    drive = ntpath.splitdrive(path)[0]

    return [os.path.join(os.environ["LOCALAPPDATA"], "rewind"),
            drive + "\\rewind-quarantine",
            os.environ["SystemRoot"],
            os.environ["ProgramFiles"],
            os.environ["ProgramFiles(x86)"]
            ]
    
    
    


def blocked_reason(tool_name: str, arguments: dict) -> str | None:
    """Return why rewind refuses this operation, or None when it may go on to the user's confirmation."""
    for path in touched_paths({"tool_name": tool_name, "arguments": arguments}):
        for folder in protected_folders(path):
            if overlaps(path, folder):
                return f"{path} lies in or contains {folder}, which rewind protects."
    return None