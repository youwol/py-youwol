from pathlib import Path
from typing import NamedTuple, Optional

from pydantic.main import BaseModel

from youwol.utils.utils_low_level import execute_shell_cmd
from youwol_utils.context import Context


class Selector(NamedTuple):
    name: Optional[str]


class Resource(BaseModel):
    name: str
    namespace: str
    revision: str
    updated: str
    status: str
    chart: str
    app_version: str


async def helm_list(namespace: Optional[str], selector: Optional[Selector], context: Optional[Context]):
    cmd = "helm list"
    if namespace:
        cmd += f" --namespace {namespace}"
    if selector and selector.name:
        cmd += f" --selector name={selector.name}"

    return_code, outputs = await execute_shell_cmd(cmd=cmd, context=context, log_outputs=False)

    def to_resource(line):
        elements = line.split("\t")
        return Resource(
            name=elements[0].strip(),
            namespace=elements[1].strip(),
            revision=elements[2].strip(),
            updated=elements[3].strip(),
            status=elements[4].strip(),
            chart=elements[5].strip(),
            app_version=elements[6]
            )
    return [to_resource(line) for line in outputs[1:] if line]


async def helm_install(release_name: str, namespace: str, values_file: Path, chart_folder: Path,
                       timeout=120, args="", context: Context = None):
    cmd = f"helm install {release_name} --create-namespace --namespace {namespace} --values {str(values_file)} " +\
          f"--atomic --timeout {timeout}s {str(chart_folder)} {args}"

    return_code, outputs = await execute_shell_cmd(cmd, context)
    return return_code, cmd, outputs


async def helm_upgrade(release_name: str, namespace: str, values_file: Path, chart_folder: Path, timeout=120, args="",
                       context: Context = None):
    cmd = f"helm upgrade {release_name} --namespace {namespace} --values {str(values_file)} " +\
          f"--atomic --timeout {timeout}s {str(chart_folder)}  {args}"

    context and context.info(text=cmd)
    return_code, outputs = await execute_shell_cmd(cmd, context)
    return return_code, cmd, outputs


async def helm_uninstall(release_name: str, namespace: str, context: Context = None):
    cmd = f"helm uninstall --namespace {namespace}  {release_name}"
    context and context.info(text=cmd)
    await execute_shell_cmd(cmd, context)


async def helm_install_or_upgrade(release_name: str, namespace: str, values_file: Path, chart_folder: Path,
                                  timeout: int, context: Context):
    _, outputs = helm_list(namespace=namespace, selector=None, context=context)
    if release_name in [r.name for r in outputs]:
        await helm_upgrade(release_name, namespace, values_file, chart_folder, timeout)
    else:
        await helm_install(release_name, namespace, values_file, chart_folder, timeout)
