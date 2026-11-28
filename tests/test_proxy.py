"""Tests for the safety gate: which proposed operations it blocks and which it lets through to the user's confirmation."""
import pytest

from rewind.executor.proxy import blocked_reason


@pytest.fixture(autouse=True)
def windows_folders(monkeypatch):
    """Fix the folders the gate reads from the environment, so the tests do not depend on the machine they run on."""
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\x\AppData\Local")
    monkeypatch.setenv("SystemRoot", r"C:\Windows")
    monkeypatch.setenv("ProgramFiles", r"C:\Program Files")
    monkeypatch.setenv("ProgramFiles(x86)", r"C:\Program Files (x86)")


BLOCKED = [
    ("delete_item", {"path": r"C:\Users\x\AppData\Local\rewind"}),
    ("delete_item", {"path": r"C:\Users\x\AppData\Local\rewind\journal.json"}),
    ("move_item", {"path": r"C:\Users\x\AppData\Local\rewind\quarantine\5\a.txt", "destination": r"C:\x\a.txt"}),
    ("delete_item", {"path": r"D:\rewind-quarantine\5\report.pdf"}),
    ("move_item", {"path": r"D:\data\a.txt", "destination": r"D:\rewind-quarantine\9\a.txt"}),
    ("rename_item", {"path": r"E:\rewind-quarantine", "new_name": "old"}),
    ("copy_item", {"path": r"C:\Users\x\AppData\Local\rewind\journal.json", "destination": r"C:\x\journal.json"}),
    ("delete_item", {"path": r"c:\windows\system32\drivers\etc\hosts"}),
    ("move_item", {"path": r"C:\Program Files\App", "destination": r"C:\x\App"}),
    ("delete_item", {"path": r"C:\Program Files (x86)\App"}),
    ("delete_item", {"path": r"C:\Users\x\AppData"}),
    ("create_archive", {"path": "C:\\", "destination": r"E:\c.zip"}),
]

ALLOWED = [
    ("create_item", {"path": r"C:\Users\x\Desktop\Backup", "kind": "directory"}),
    ("delete_item", {"path": r"D:\data\old.log"}),
    ("delete_item", {"path": r"C:\Windows2\notes.txt"}),
    ("delete_item", {"path": r"C:\Program Files Extra\notes.txt"}),
    ("rename_item", {"path": r"C:\x\a.txt", "new_name": "rewind-quarantine"}),
    ("start_process", {"program": "notepad"}),
    ("stop_process", {"name": "notepad"}),
]


@pytest.mark.parametrize("tool_name, arguments", BLOCKED)
def test_blocks_operations_that_touch_a_protected_folder(tool_name, arguments):
    assert blocked_reason(tool_name, arguments) is not None


@pytest.mark.parametrize("tool_name, arguments", ALLOWED)
def test_lets_ordinary_operations_through(tool_name, arguments):
    assert blocked_reason(tool_name, arguments) is None


def test_reason_names_the_path_and_the_protected_folder():
    reason = blocked_reason("delete_item", {"path": r"D:\rewind-quarantine\5"})
    assert reason == r"D:\rewind-quarantine\5 lies in or contains D:\rewind-quarantine, which rewind protects."