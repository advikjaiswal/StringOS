# tools/file_ops.py
from tools.base import Tool
import os

class FileLister(Tool):
    def __init__(self):
        super().__init__("list_files")

    def run(self, directory="."):
        try:
            files = os.listdir(directory)
            return {"status": "success", "files": files}
        except Exception as e:
            return {"status": "error", "error": str(e)}
