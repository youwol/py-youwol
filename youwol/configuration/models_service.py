from typing import Dict, Callable, Any

from youwol.configuration.models_base import Target, Action, Context


class TargetService(Target):
    basePath: str = None
    port: int = None


URL = str


class Serve(Action):
    health: URL = None
    openApi: Callable[[Any, Context], str] = None

    def open_api(self, resource: Any, context: Context):
        if not self.openApi:
            return None

        return self.openApi(resource, context)


def get_target_from_base_path(base_path: str, targets: Dict[str, any]):

    def from_category(_targets):
        return (t for t in _targets if t.basePath == base_path)

    look_up = ((category, next(from_category(targets)))
               for category, targets in targets.items()
               if any(from_category(targets)))

    target = next(look_up)
    return target
