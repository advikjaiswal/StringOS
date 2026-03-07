# tool_runner.py
from tools.file_ops import FileLister

TOOL_REGISTRY = {
    "list_files": FileLister(),
}

def run_tool(tool_name, **kwargs):
    tool = TOOL_REGISTRY.get(tool_name)
    if not tool:
        return {"status": "error", "error": f"Tool '{tool_name}' not found."}
    return tool.run(**kwargs)
