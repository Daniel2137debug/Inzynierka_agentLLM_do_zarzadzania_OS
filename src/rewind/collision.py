"""The collision rule for /undo: a later operation that touched the same files blocks it - paths only, no disk or journal access."""
import ntpath


def overlaps(first: str, second: str) -> bool:
    """True when two paths name the same item or one lies inside the other; Windows ignores letter case in paths."""
    first = ntpath.normcase(first)
    second = ntpath.normcase(second)

    if first == second:
        return True
    elif first.startswith(second.rstrip("\\") + "\\") or second.startswith(first.rstrip("\\") + "\\"):
        return True
    else:
        return False

def touched_paths(record: dict) -> list[str]:
    """Every path an operation acted on: rename_item also put the item at a new path; process tools touch none."""
    arguments = record["arguments"]
    #because processes dont have any path so threre is if field in arguments check to avoid KeyError. Also rename_item has new_name field so we need to add it to the list of paths
    paths = [arguments[field] for field in ("path", "destination") if field in arguments] 
    if record["tool_name"] == "rename_item":
        #this tool save only the new name of the file, so here we build the full path of it consist of path to the file and new name of it. We use ntpath.join to join them together. We also use ntpath.dirname to get the directory of the file from the path, so we can join it with the new name of the file.
        paths.append(ntpath.join(ntpath.dirname(arguments["path"]), arguments["new_name"]))
    return paths


def find_collision(record: dict, later_records: list[dict]) -> dict | None:
    """Return the first later operation whose paths overlap this record's paths, or None when undo may go ahead."""
    for later in later_records:
        for path in touched_paths(record):
            for later_path in touched_paths(later):
                if overlaps(path, later_path):
                    return later
    return None