
from rewind.schemas.tools import RenameItem, CreateItem
from typing import Literal
import ollama
from rewind.environment import get_env_data



TOOLS = {
    "rename_item": RenameItem,
    "create_item": CreateItem,
}

def build_definitions() -> list[dict]:
    """Turn the tool registry into the list of tool definitions the model receives."""
    definitions = []
    for name, schema_class in TOOLS.items():
        tool_schema = schema_class.model_json_schema()
        definitions.append({
            "type": "function",
            "function": {
                "name": name,
                "description": tool_schema["description"],
                "parameters": tool_schema
            }
        })  
    return definitions

def build_system_prompt(env: dict[str,str]) -> str:
    """Set system prompt on the first position in "messages" list. It will be valid for whole conversation with user"""
    
    return f"""You are a Windows assistant. You act by selecting one of the tools available to you. 

Current environment:
home directory:    {env["home_dir"]}
desktop directory: {env["desktop_dir"]} 
working directory: {env["current_dir"]}
operating system:  {env["os_name"]} {env["os_version"]}
administrator:     {env["is_admin"]}

Resolve locations the user names, such as "my Desktop" or "here", using the paths above. Every path you pass to a tool must be absolute. If the user names something that is not listed above, pass it through exactly as given; never invent a missing part of a path.
"""
    

class Adapter:
    """Start using llm model and whole conversation"""
    def __init__(self, model: str) -> None:
        self.model = model
        self.conversation_history: list[dict] = [] 

    def add_message(self, role: Literal["system", "user", "assistant"], content: str |None = None, tool_calls: list | None = None) -> None:
        """Add message to the conversation. If tool_calls is not None, it will be added as a tool call from the assistant. If tool_calls is None, it will be added as a message from the user or assistant."""
        message = {"role": role}
        if tool_calls is not None:
            message["tool_calls"] = tool_calls
        else:
            message["content"] = content
        self.conversation_history.append(message)

    def start_system_prompt(self, env: dict[str,str]) -> None:
        """Start conversation with system prompt"""
        system_prompt = build_system_prompt(env)
        self.add_message(role="system", content=system_prompt)

    def run_conversation(self, user_prompt: str | None = None) -> tuple[str, dict] | None:
        """Run the conversation with the model. If user_prompt is provided, it will be added to the conversation history. The function returns either the assistant's response or a tuple of (tool_name, tool_arguments) if a tool call is made."""
        if user_prompt:
            self.add_message(role="user", content=user_prompt)
        ollama_response = ollama.chat(model=self.model, messages=self.conversation_history, tools=build_definitions())
        self.add_message(role="assistant", content=ollama_response.message.content, tool_calls=ollama_response.message.tool_calls)
        if not ollama_response.message.tool_calls:
            return ollama_response.message.content
        results = []
        for tool_call in ollama_response.message.tool_calls:
            tool_name = tool_call.function.name
            if tool_name not in TOOLS:
                raise ValueError(f"Tool '{tool_name}' is not registered.")
            schema_class = TOOLS[tool_name]
            validated = schema_class.model_validate(tool_call.function.arguments)
            results.append((tool_name, validated))
            
        return results
                
                    
                

        


                