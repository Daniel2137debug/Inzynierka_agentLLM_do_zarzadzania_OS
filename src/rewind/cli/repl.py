from rich.console import Console
from rewind.adapter.adapter_ollama import Adapter
from rewind.commands.create_item import CreateItemCommand
from rewind.storage.journal import Journal
console = Console()

def run_repl(adapter: Adapter) -> None:
    """Read a user prompts, show the model's proposals and ask for confirmation."""
    console.print("rewind ready - type /quit to exit", style="dim")
    journal = Journal()

    while True:
        user_prompt = console.input("[bold cyan]>>>[/] ").strip()
        if not user_prompt:
            continue

        if user_prompt == "/quit":
            console.print("Exiting REPL...", style="dim")
            break

        with console.status("[dim]thinking...[/]", spinner="dots"):
            result = adapter.run_conversation(user_prompt)
        if not result:
            console.print("No response from the model.", style="red")
            continue
        if isinstance(result, str):
            console.print(f"[bold green]Model response:[/] {result}")
            continue

        for tool_name, validated in result:
            console.print(f"\n[bold yellow]{tool_name}[/]")

            for field, value in validated.model_dump().items():
                console.print(f"  {field}: {value}")

            answer = console.input("\nExecute? (y/n): ").strip().lower()

            if answer != "y":
                console.print(f"Rejected {tool_name}.", style="red")
                continue

            record_id = journal.write_pending(tool_name, validated.model_dump())

            command = CreateItemCommand(validated)
            success, output = command.execute()

            if success:
                journal.mark_success(record_id)
                console.print(f"Done. {output}", style="green")
            else:
                journal.mark_failed(record_id)
                console.print(f"Failed: {output}", style="red")