# tools/base.py
class Tool:
    def __init__(self, name):
        self.name = name

    def run(self, **kwargs):
        raise NotImplementedError("Tool must implement `run()` method.")
