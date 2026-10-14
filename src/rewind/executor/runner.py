import subprocess


def run_powershell(command: str) -> tuple[bool, str]:
    """Run a PowerShell command and report whether it succeeded, plus its output.

    On failure the returned text is PowerShell's own stderr, so the user sees the
    real reason instead of a paraphrase of it.
    """
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
    )

    if completed.returncode != 0:
        return False, completed.stderr.strip()

    return True, completed.stdout.strip()