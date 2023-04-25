# Youwol application
from youwol.app.environment import (
    Command,
    Configuration,
    CustomEndPoints,
    Customization,
    LocalEnvironment,
    Projects,
    RecursiveProjectsFinder,
    System,
)
from youwol.app.environment.models.predefined_configs.py_youwol_tour.common import (
    clone_project,
)
from youwol.app.environment.models.predefined_configs.py_youwol_tour.starter import (
    init_working_folders,
)

root_folder, cache_folder, projects_folder, ecosystem_folder = init_working_folders()

Configuration(
    projects=Projects(
        finder=RecursiveProjectsFinder(
            fromPaths=[projects_folder],
        )
    ),
    system=System(
        localEnvironment=LocalEnvironment(
            dataDir=ecosystem_folder, cacheDir=cache_folder
        )
    ),
    customization=Customization(
        endPoints=CustomEndPoints(
            commands=[
                Command(
                    name="git-clone-todo-app-js",
                    do_post=lambda body, ctx: clone_project(
                        repo_name="todo-app-js",
                        parent_folder=projects_folder,
                        context=ctx,
                    ),
                ),
            ]
        )
    ),
)
