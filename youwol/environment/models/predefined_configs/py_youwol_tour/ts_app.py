from youwol.environment import Configuration, System, LocalEnvironment, Projects, RecursiveProjectsFinder, \
    Customization, CustomEndPoints, Command, FlowSwitcherMiddleware
from youwol.environment.models.predefined_configs.py_youwol_tour.common import clone_project
from youwol.environment.models.predefined_configs.py_youwol_tour.starter import init_working_folders
from youwol.pipelines.pipeline_typescript_weback_npm.regular.webpack_dev_server_switch import WebpackDevServerSwitch
import youwol.pipelines.pipeline_typescript_weback_npm as pipeline_ts

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
            dataDir=ecosystem_folder,
            cacheDir=cache_folder
        )
    ),
    customization=Customization(
        middlewares=[
            FlowSwitcherMiddleware(
                name="Frontend servers",
                oneOf=[WebpackDevServerSwitch(packageName="@youwol/todo-app-ts", port=4001)]
            )
        ],
        endPoints=CustomEndPoints(
            commands=[
                Command(
                    name="git-clone-todo-app-ts",
                    do_post=lambda body, ctx: clone_project(repo_name="todo-app-ts", parent_folder=projects_folder,
                                                            context=ctx)
                ),
            ]
        )
    )
)
