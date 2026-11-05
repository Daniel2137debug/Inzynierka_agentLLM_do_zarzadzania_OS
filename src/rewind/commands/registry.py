from rewind.commands.base import BaseCommand
from rewind.commands.copy_item import CopyItemCommand
from rewind.commands.create_archive import CreateArchiveCommand
from rewind.commands.create_item import CreateItemCommand
from rewind.commands.delete_item import DeleteItemCommand
from rewind.commands.move_item import MoveItemCommand
from rewind.commands.rename_item import RenameItemCommand


# TOOLS is what the model sees, COMMANDS is what actually runs.
COMMANDS: dict[str, type[BaseCommand]] = {
    "create_item": CreateItemCommand,
    "rename_item": RenameItemCommand,
    "delete_item": DeleteItemCommand,
    "move_item": MoveItemCommand,
    "copy_item": CopyItemCommand,
    "create_archive": CreateArchiveCommand,
}