import os
import pathlib
import datetime
from tinydb import Query, TinyDB
from tinydb.table import Document



class Journal:
    _instance = None
    def __new__(cls):

        if cls._instance is None:
            localisation = os.path.join(os.getenv("LOCALAPPDATA"), "rewind")
            pathlib.Path(localisation).mkdir(parents=True, exist_ok=True) 
            cls._instance = super(Journal, cls).__new__(cls)
            cls._instance.db = TinyDB(os.path.join(localisation, "journal.json"))
      
        return cls._instance


    def write_pending(self, tool_name: str, arguments: dict) -> int:
        """Write a pending record to the journal."""
        document = {
            "tool_name": tool_name,
            "arguments": arguments,
            "undo_payload": {},
            "status": "pending",
            "timestamp": datetime.datetime.now().isoformat(),
            "undone": False
        }
        return self.db.insert(document)

    def mark_success(self, record_id: int, undo_payload: dict) -> None:
        """Mark a record as successful and store what undo() needs - the only write of the payload."""
        self.db.update({"status": "success", "undo_payload": undo_payload}, doc_ids=[record_id]) 


    def mark_failed(self, record_id: int) -> None:
        """Mark a record as failed in the journal."""
        self.db.update({"status": "failed"}, doc_ids=[record_id])

    def next_to_undo(self, skip_tools: set[str]) -> Document | None:
        """Return the record /undo takes next: the newest success not undone yet, skipping irreversible tools."""
        record = Query()
        #one_of() is Tinydb equivalent of regular "in" operator. we added ~ to invert the condition, so finally it means "not in skip_tools" - we want to skip irreversible tools
        candidates = self.db.search((record.status == "success") & (record.undone == False) & ~record.tool_name.one_of(skip_tools))
        if not candidates:
            return None
        return max(candidates, key=lambda candidate: candidate.doc_id)
        #lambda cuz its a list so every element needs to goes through the function and the result what lambda return will be comared

    def mark_undone(self, record_id: int) -> None:
        """Flag a record as undone; the record itself stays in the journal."""
        self.db.update({"undone": True}, doc_ids=[record_id])

    def all_records(self) -> list[Document]:
        """Return every record in the journal, oldest first."""
        return sorted(self.db.all(), key=lambda record: record.doc_id)