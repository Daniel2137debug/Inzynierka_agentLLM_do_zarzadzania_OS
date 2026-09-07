
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
