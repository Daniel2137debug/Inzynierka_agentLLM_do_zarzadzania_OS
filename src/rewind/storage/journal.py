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
            cls._instance.messages = cls._instance.db.table("messages")
      
        return cls._instance


    def write_pending(self, tool_name: str, arguments: dict, session_id: int) -> int:
        """Write a pending record to the journal, tagged with the session it belongs to."""
        document = {
            "tool_name": tool_name,
            "arguments": arguments,
            "undo_payload": {},
            "status": "pending",
            "timestamp": datetime.datetime.now().isoformat(),
            "undone": False,
            "session_id": session_id,
        }
        return self.db.insert(document)

    def mark_success(self, record_id: int, undo_payload: dict) -> None:
        """Mark a record as successful and store what undo() needs - the only write of the payload."""
        self.db.update({"status": "success", "undo_payload": undo_payload}, doc_ids=[record_id]) 


    def mark_failed(self, record_id: int) -> None:
        """Mark a record as failed in the journal."""
        self.db.update({"status": "failed"}, doc_ids=[record_id])

    def next_to_undo(self, skip_tools: set[str], session_id: int) -> Document | None:
        """Return the record /undo takes next in this session: its newest success not undone yet, skipping irreversible tools."""
        record = Query()
        #one_of() is Tinydb equivalent of regular "in" operator. we added ~ to invert the condition, so finally it means "not in skip_tools" - we want to skip irreversible tools
        #& unstead of and because Tinydb uses its own Query object, so we need to use & to combine conditions
        candidates = self.db.search((record.session_id == session_id) & (record.status == "success") & (record.undone == False) & ~record.tool_name.one_of(skip_tools))
        if not candidates:
            return None
        return max(candidates, key=lambda candidate: candidate.doc_id)
        #lambda cuz its a list so every element needs to goes through the function and the result what lambda return will be comared

    def mark_undone(self, record_id: int) -> None:
        """Flag a record as undone; the record itself stays in the journal."""
        self.db.update({"undone": True}, doc_ids=[record_id])

    def session_records(self, session_id: int) -> list[Document]:
        """Return every record of one session, oldest first."""
        return sorted(self.db.search(Query().session_id == session_id), key=lambda record: record.doc_id)

    def active_records_after(self, record_id: int) -> list[Document]:
        """Return the records newer than this one whose operations are still on disk - success, not undone - in every session."""
        record = Query()
        active = self.db.search((record.status == "success") & (record.undone == False))
        return sorted([later for later in active if later.doc_id > record_id], key=lambda later: later.doc_id)

    def add_message(self, session_id: int, message: dict) -> None:
        """Append one message of the conversation to its session; messages are never changed afterwards."""
        self.messages.insert({
            "session_id": session_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "message": message,
        })

    def last_messages(self, session_id: int, limit: int) -> list[Document]:
        """Return the newest messages of a session, at most `limit`, oldest first - what a resumed session gets back."""
        rows = self.messages.search(Query().session_id == session_id)
        rows.sort(key=lambda row: row.doc_id)
        return rows[-limit:]

    def new_session_id(self) -> int:
        """Return the number for a new session: one above the highest so far, so the first session is 1."""
        return max((row["session_id"] for row in self.messages.all()), default=0) + 1

    def list_sessions(self) -> list[tuple[int, str, str]]:
        """Return every session as (number, first prompt, time of its last message), most recently active first."""
        first_prompts = {}
        last_rows = {}
        for row in sorted(self.messages.all(), key=lambda row: row.doc_id):
            number = row["session_id"]
            if number not in first_prompts and row["message"]["role"] == "user":
                first_prompts[number] = row["message"]["content"]
            last_rows[number] = row
        newest_first = sorted(last_rows, key=lambda number: last_rows[number].doc_id, reverse=True)
        return [(number, first_prompts[number], last_rows[number]["timestamp"]) for number in newest_first]