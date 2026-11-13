
import ntpath
from typing import Annotated, Literal

from pydantic import BaseModel, Field, AfterValidator

NormalizedPath = Annotated[str, AfterValidator(ntpath.normpath)]


class CreateItem(BaseModel):
    """Create a new, empty file or directory at the specified absolute path."""
    path: NormalizedPath = Field(
        min_length=1, description="Absolute path where the item will be created, including the new item's own name, e.g. C:/Users/<username>/Desktop/Backup"
        #those limitations on fileds like min_length=1 works on already delivered data by model not on the data that is being delivered to model, so if model get empty string in prompt it will be accepted and then data will raise error on validation in tools
    )
    #Decided to pick word "kind" instead of "type" to avoid confusion with Python's built-in type() function.
    kind: Literal["directory", "file"] = Field(
        description="The kind of the item to create, either 'directory' or 'file'."
    )





class RenameItem(BaseModel):
    """Rename a single existing item, keeping it in the same directory"""
    path: NormalizedPath = Field(
        min_length=1, description="Absolute path to the item to rename, e.g. C:/Users/<username>/report.pdf"
    )
   
    new_name: str = Field(
        min_length=1, description="The new item name including the extension, without any directory part."
    )
    
#in RenameItem we dont need "kind" field cuz it doesnt matter if we rename a file or a directory, the operation is the same. However even if - in case of other tools - there would be a diffrence between operations datas will be taken from system




class DeleteItem(BaseModel):
    """Delete a single existing file or directory, including everything inside it."""
    path: NormalizedPath = Field(
        min_length=1, description="Absolute path to the item to delete, e.g. C:/Users/<username>/Desktop/old_notes.txt"
    )


class MoveItem(BaseModel):
    """Move a single existing file or directory to a new location."""
    path: NormalizedPath = Field(
        min_length=1, description="Absolute path to the item to move, e.g. C:/Users/<username>/Desktop/report.pdf"
    )
    destination: NormalizedPath = Field(
        min_length=1, description="Absolute path the item will have after the move, including its own name, e.g. C:/Users/<username>/Documents/report.pdf"
    )


class CopyItem(BaseModel):
    """Copy a single existing file or directory, with everything inside it, to a new location."""
    path: NormalizedPath = Field(
        min_length=1, description="Absolute path to the item to copy, e.g. C:/Users/<username>/Desktop/report.pdf"
    )
    destination: NormalizedPath = Field(
        min_length=1, description="Absolute path the copy will have, including its own name, e.g. C:/Users/<username>/Documents/report_copy.pdf"
    )

class CreateArchive(BaseModel):
    """Pack a single existing file or directory into a new .zip archive."""
    path: NormalizedPath = Field(
        min_length=1, description="Absolute path to the file or directory to pack, e.g. C:/Users/<username>/Desktop/Photos"
    )
    destination: NormalizedPath = Field(
        min_length=1, description="Absolute path of the new archive, ending with .zip, e.g. C:/Users/<username>/Desktop/Photos.zip"
    )

class StartProcess(BaseModel):
    """Start a program and leave it running."""
    program: str = Field(
        min_length=1, description="The program to start, without any arguments: its short name, e.g. excel or charmap. Use a full path only if the user typed one; never guess a path."
    )

class StopProcess(BaseModel):
    """Stop a running program at once. This cannot be undone: unsaved work in that program is lost."""
    name: str = Field(
        min_length=1, description="The name of the running program, as Task Manager shows it, without .exe - e.g. notepad or charmap"
    )