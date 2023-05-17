# Youwol application
from youwol.app.environment import (
    Command,
    Configuration,
    CustomEndPoints,
    Customization,
    FlowSwitcherMiddleware,
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

# Youwol pipelines
import youwol.pipelines.pipeline_typescript_weback_npm as pipeline_ts

from youwol.pipelines.pipeline_typescript_weback_npm.regular.webpack_dev_server_switch import (
    WebpackDevServerSwitch,
)

pipeline_ts.set_environment()

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
        middlewares=[
            FlowSwitcherMiddleware(
                name="Frontend servers",
                oneOf=[
                    WebpackDevServerSwitch(packageName="@youwol/todo-app-ts", port=4001)
                ],
            )
        ],
        endPoints=CustomEndPoints(
            commands=[
                Command(
                    name="git-clone-todo-app-ts",
                    do_post=lambda body, ctx: clone_project(
                        repo_name="todo-app-ts",
                        parent_folder=projects_folder,
                        context=ctx,
                    ),
                ),
            ]
        ),
    ),
)
