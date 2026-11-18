from rich.console import Console
from rewind.adapter.adapter_ollama import TOOLS, Adapter
from rewind.commands.registry import COMMANDS
from rewind.storage.journal import Journal
from rich.markup import escape
from rich.table import Table



console = Console()

# Tools whose records /undo skips - irrevesible ones like StopProcess
IRREVERSIBLE_TOOLS = {name for name, command in COMMANDS.items() if not command.can_undo}

def undo_last(journal: Journal) -> None:
    """Undo the newest successful operation from the journal, after the user confirms it."""
    record = journal.next_to_undo(IRREVERSIBLE_TOOLS)
    if record is None:
        console.print("Nothing to undo.", style="yellow")
        return

    #that just a timestamp format
    done_at = record["timestamp"][:19].replace("T", " ")
    console.print(f"\n[bold yellow]undo {record['tool_name']}[/] [dim](done {done_at})[/]")
    for field, value in record["arguments"].items():
        console.print(f"  {field}: {escape(str(value))}")

    if COMMANDS[record["tool_name"]].undo_note:
        console.print(COMMANDS[record["tool_name"]].undo_note, style="yellow")

    answer = console.input("\nUndo? (y/n): ").strip().lower()
    if answer != "y":
        console.print("Undo cancelled.", style="red")
        return


    tool_name = record["tool_name"]
    arguments = TOOLS[tool_name].model_validate(record["arguments"])
    command = COMMANDS[tool_name](arguments, record.doc_id, record["undo_payload"])
    success, output = command.undo()

    if success:
        journal.mark_undone(record.doc_id)
        console.print(f"Undone. {escape(output)}", style="green")
    else:
        console.print(f"Undo refused: {escape(output)}", style="red")

STATUS_STYLES = {"success": "green", "failed": "red", "pending": "yellow"}


def show_history(journal: Journal) -> None:
    """Print the journal as a table and mark the record /undo would take next."""
    records = journal.all_records()
    if not records:
        console.print("The journal is empty.", style="dim")
        return

    next_record = journal.next_to_undo(IRREVERSIBLE_TOOLS)
    table = Table(title="Operation journal")
    for column in ("#", "time", "tool", "arguments", "status", "undo"):
        table.add_column(column)

    for record in reversed(records):
    
        arguments = ", ".join(f"{field}={value}" for field, value in record["arguments"].items())
        status = record["status"]
        if record["undone"]:
            undo_state = "undone"
        elif record["tool_name"] in IRREVERSIBLE_TOOLS:
            undo_state = "[dim]irreversible[/]"
        elif next_record is not None and record.doc_id == next_record.doc_id:
            undo_state = "[bold]next[/]"
        else:
            undo_state = ""
        table.add_row(
            str(record.doc_id),
            record["timestamp"][:19].replace("T", " "),
            record["tool_name"],
            escape(arguments),
            f"[{STATUS_STYLES.get(status, 'white')}]{status}[/]",
            undo_state,
        )

    console.print(table)


# Number says how many messages of the session to show when resuming it. The newest ones are shown so the user sees the context of the last few exchanges.
HISTORY_WINDOW = 20


def show_sessions(sessions: list[tuple[int, str, str]]) -> None:
    """Print sessions one per line: number, first prompt and, in small print, when the session was last active."""
    for number, first_prompt, last_active in sessions:
        console.print(f"  {number}  {escape(first_prompt[:60])}  [dim]{last_active[:16].replace('T', ' ')}[/]")


def show_messages(rows: list[dict]) -> None:
    """Print a resumed session's messages the way they looked live, each prompt with its date in small print."""
    for row in rows:
        message = row["message"]
        if message["role"] == "user":
            console.print(f"[bold cyan]>>>[/] {escape(message['content'])}")
            console.print(f"    {row['timestamp'][:16].replace('T', ' ')}", style="dim")
        elif "tool_calls" in message:
            for call in message["tool_calls"]:
                console.print(f"[bold yellow]{call['function']['name']}[/]")
                for field, value in call["function"]["arguments"].items():
                    console.print(f"  {field}: {escape(str(value))}")
        elif message.get("content"):
            console.print(f"[bold green]Model response:[/] {escape(message['content'])}")


def choose_session(journal: Journal, adapter: Adapter) -> int:
    """Before the REPL starts, offer the most recent sessions: a number resumes one, Enter starts a new one. Return its number."""
    sessions = journal.list_sessions()
    if not sessions:
        return journal.new_session_id()

    console.print("Recent sessions:", style="dim")
    show_sessions(sessions[:3])
    numbers = {number for number, _, _ in sessions}
    while True:
        answer = console.input("Session number to resume, 'more' to list all, or click Enter for a new one: ").strip().lower()
        if not answer:
            return journal.new_session_id()
        if answer == "more":
            show_sessions(sessions)
            continue
        # first condition check if the answer is a digit and second condition check if the number is in the list of sessions numbers bc fi 7 is a digit but it wouldnt be in the list of sessions 
        if answer.isdigit() and int(answer) in numbers:
            break
        console.print(f"There is no session {escape(answer)}.", style="red")

    session_id = int(answer)
    rows = journal.last_messages(session_id, HISTORY_WINDOW)
    show_messages(rows)
    adapter.restore_messages([row["message"] for row in rows])
    return session_id


def run_repl(adapter: Adapter) -> None:
    """Read a user prompts, show the model's proposals and ask for confirmation."""
    journal = Journal()
    session_id = choose_session(journal, adapter)
    console.print(f"session {session_id} - /history, /undo, /quit", style="dim")

    while True:
        user_prompt = console.input("[bold cyan]>>>[/] ").strip()
        if not user_prompt:
            continue

        if user_prompt == "/quit":
            console.print("Exiting REPL...", style="dim")
            break

        if user_prompt == "/undo":
            undo_last(journal)
            continue

        if user_prompt == "/history":
            show_history(journal)
            continue

        history_length = len(adapter.conversation_history)
        try:
            with console.status("[dim]thinking...[/]", spinner="dots"):
                result = adapter.run_conversation(user_prompt)
        except ValueError as error:
            # An unregistered tool or arguments that fail validation
            console.print(f"The model proposed something rewind cannot run:\n{escape(str(error))}", style="red")
            continue
        finally:
            # Save what this turn added - the prompt and the model's answer - even when the answer failed validation
            # Before model's run we save the length of the conversation history and after model's run we save everything aboove that lenght what the raw added so users prompt and model's anwer
            for message in adapter.conversation_history[history_length:]:
                journal.add_message(session_id, message)


        if not result:
            console.print("No response from the model.", style="red")
            continue
        if isinstance(result, str):
            console.print(f"[bold green]Model response:[/] {escape(result)}")
            continue

        for tool_name, validated in result:
            console.print(f"\n[bold yellow]{tool_name}[/]")

            if tool_name not in COMMANDS:
                console.print(f"{tool_name} has no command behind it yet.", style="yellow")
                continue

            for field, value in validated.model_dump().items():
                console.print(f"  {field}: {escape(str(value))}")

            if tool_name in IRREVERSIBLE_TOOLS:
                console.print("This operation cannot be undone.", style="bold red")

            answer = console.input("\nExecute? (y/n): ").strip().lower()

            if answer != "y":
                console.print(f"Rejected {tool_name}.", style="red")
                continue

            record_id = journal.write_pending(tool_name, validated.model_dump(), session_id)

            command = COMMANDS[tool_name](validated, record_id)
            success, output = command.execute()

            if success:
                journal.mark_success(record_id, command.undo_payload)
                console.print(f"Done. {escape(output)}", style="green")
            else:
                journal.mark_failed(record_id)
                console.print(f"Failed: {escape(output)}", style="red")