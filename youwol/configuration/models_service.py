from typing import Dict, Callable, Any

from youwol.configuration.models_base import Target, Action, Context


class TargetService(Target):
    basePath: str = None
    port: int = None


URL = str


class Serve(Action):

    health: URL = None
    openApi: Callable[[Any, Context], str] = None
    mapper_end_points: Callable[[str, Target, Context], str] = None

    def open_api(self, resource: Any, context: Context):
        if not self.openApi:
            return None

        return self.openApi(resource, context)

    def end_point(self, rest_of_path: str, target: Target, context: Context) -> str:
        if not self.mapper_end_points:
            return rest_of_path
        return self.mapper_end_points(rest_of_path, target, context)


def get_target_from_base_path(base_path: str, targets: Dict[str, any]):

    def from_category(_targets):
        return (t for t in _targets if t.basePath == base_path)

    look_up = ((category, next(from_category(targets)))
               for category, targets in targets.items()
               if any(from_category(targets)))

    target = next(look_up)
    return target
