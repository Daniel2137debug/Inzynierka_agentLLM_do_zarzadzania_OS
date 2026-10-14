import typer
from rewind.adapter.adapter_ollama import Adapter
from rewind.environment import get_env_data
from rewind.cli.repl import run_repl

app = typer.Typer()

@app.command()
def start(model: str = "llama3.1:8b") -> None:
    """Start the assistant with the specified model. The default model is "llama3.1:8b". You can specify a different model by providing its name as an argument.
    Example: python main.py start --model "llama3.1:13b"
    """
    adapter = Adapter(model=model)
    adapter.start_system_prompt(env=get_env_data())

    run_repl(adapter)
