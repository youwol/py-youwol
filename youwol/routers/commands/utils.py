from enum import Enum


class ActionType(Enum):
    run = "run"


icons_factory = {
    ActionType.run: 'fas fa-play'
    }


