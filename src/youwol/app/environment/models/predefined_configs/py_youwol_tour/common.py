# standard library
from pathlib import Path

# Youwol utilities
from youwol.utils import Context, execute_shell_cmd


async def clone_project(repo_name: str, parent_folder: Path, context: Context):
    """
    :param repo_name: url to clone
    :param parent_folder: folder in which the repository is cloned
    :param context: context (essentially to log)
    :return: {'returnCode': return code of git clone command, 'outputs': outputs of git clone command }
    """
    async with context.start(action=f"clone repo {repo_name}") as ctx:  # type: Context
        url = f"https://github.com/youwol/{repo_name}.git"
        return_code, outputs = await execute_shell_cmd(
            cmd=f"(cd {parent_folder} && git clone {url})", context=ctx
        )
        resp = {"returnCode": return_code, "outputs": outputs}
        if not (parent_folder / repo_name).exists():
            raise RuntimeError("Git repo not properly cloned")

        await ctx.info(text="repo cloned", data=resp)

    return resp
