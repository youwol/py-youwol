import shutil
from pathlib import Path

from youwol.environment import Configuration, Projects, \
    RecursiveProjectsFinder, System, LocalEnvironment, Customization, CustomEndPoints, Command, \
    FlowSwitcherMiddleware,  CdnSwitch
from youwol.pipelines.pipeline_typescript_weback_npm import lib_ts_webpack_template, app_ts_webpack_template
from youwol_utils import Context, execute_shell_cmd

root_folder = Path('/tmp/py-youwol-story-env')
root_folder.exists() and shutil.rmtree(root_folder)
root_folder.mkdir(parents=True, exist_ok=True)
projects_folder = root_folder / "Projects"
projects_folder.mkdir()


async def clone_project(repo_name: str, context: Context):
    """
    :param repo_name: url to clone
    :param context: context (essentially to log)
    :return: {'returnCode': return code of git clone command, 'outputs': outputs of git clone command }
    """
    async with context.start(action=f"clone repo {repo_name}") as ctx:  # type: Context
        url = f"https://github.com/youwol/{repo_name}.git"
        return_code, outputs = await execute_shell_cmd(cmd=f"(cd {projects_folder} && git clone {url})",
                                                       context=ctx)
        resp = {"returnCode": return_code, "outputs": outputs}
        if not (projects_folder / repo_name).exists():
            raise RuntimeError("Git repo not properly cloned")

        await ctx.info(text="repo cloned", data=resp)

    return resp


Configuration(
    projects=Projects(
        finder=RecursiveProjectsFinder(
            fromPaths=[projects_folder],
        ),
        templates=[
            lib_ts_webpack_template(folder=projects_folder),
            app_ts_webpack_template(folder=projects_folder)
        ]
    ),
    system=System(
        localEnvironment=LocalEnvironment(
            dataDir=root_folder / 'data',
            cacheDir=root_folder / 'cache'
        )
    ),
    customization=Customization(
        middlewares=[
            FlowSwitcherMiddleware(
                name="Frontend servers",
                oneOf=[CdnSwitch(packageName="@youwol/todo-app-ts", port=4001)]
            )
        ],
        endPoints=CustomEndPoints(
            commands=[
                Command(
                    name="git-clone-todo-app-js",
                    do_post=lambda body, ctx: clone_project(repo_name="todo-app-js", context=ctx)
                ),
                Command(
                    name="git-clone-todo-app-ts",
                    do_post=lambda body, ctx: clone_project(repo_name="todo-app-ts", context=ctx)
                )
            ]
        )
    )
)
