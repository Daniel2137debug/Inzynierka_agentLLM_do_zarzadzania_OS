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


def run_repl(adapter: Adapter) -> None:
    """Read a user prompts, show the model's proposals and ask for confirmation."""
    console.print("rewind ready - /history, /undo, /quit", style="dim")
    journal = Journal()

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

        try:
            with console.status("[dim]thinking...[/]", spinner="dots"):
                result = adapter.run_conversation(user_prompt)
        except ValueError as error:
            # An unregistered tool or arguments that fail validation
            console.print(f"The model proposed something rewind cannot run:\n{escape(str(error))}", style="red")
            continue
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

            record_id = journal.write_pending(tool_name, validated.model_dump())

            command = COMMANDS[tool_name](validated, record_id)
            success, output = command.execute()

            if success:
                journal.mark_success(record_id, command.undo_payload)
                console.print(f"Done. {escape(output)}", style="green")
            else:
                journal.mark_failed(record_id)
                console.print(f"Failed: {escape(output)}", style="red")