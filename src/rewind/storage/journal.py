import os
import pathlib
import datetime
from tinydb import TinyDB



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

    def mark_success(self, record_id: int) -> None:
        """Mark a record as successful in the journal."""
        self.db.update({"status": "success"}, doc_ids=[record_id])  


    def mark_failed(self, record_id: int) -> None:
        """Mark a record as failed in the journal."""
        self.db.update({"status": "failed"}, doc_ids=[record_id])