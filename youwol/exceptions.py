from typing import List, Any


class CommandException(Exception):
    def __init__(self, command: str, outputs: List[str]):
        self.command = command
        self.outputs = outputs
        super().__init__(f"{self.command} failed")


class ActionException(Exception):
    def __init__(self, action: str, message: str):
        self.action = action
        self.message = message
        super().__init__(self.message)


class UserCodeException(Exception):
    def __init__(self, message: str, tb: Any):
        self.traceback = tb
        self.message = message
        super().__init__(self.message)

