# standard library
from pathlib import Path

# typing
from typing import NamedTuple, Optional

# third parties
from pydantic.main import BaseModel

# Youwol utilities
from youwol.utils.context import Context
from youwol.utils.utils_shell import execute_shell_cmd


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


async def helm_list(
    namespace: Optional[str],
    kube_context: str,
    selector: Optional[Selector],
    context: Context,
):
    cmd = f"helm list --kube-context {kube_context}"
    if namespace:
        cmd += f" --namespace {namespace}"
    if selector and selector.name:
        cmd += f" --selector name={selector.name}"

    _, outputs = await execute_shell_cmd(cmd=cmd, context=context, log_outputs=False)

    def to_resource(line):
        elements = line.split("\t")
        return Resource(
            name=elements[0].strip(),
            namespace=elements[1].strip(),
            revision=elements[2].strip(),
            updated=elements[3].strip(),
            status=elements[4].strip(),
            chart=elements[5].strip(),
            app_version=elements[6],
        )

    return [to_resource(line) for line in outputs[1:] if line]


async def helm_dry_run(
    release_name: str,
    namespace: str,
    values_file: Path,
    chart_folder: Path,
    context: Context,
    args="",
):
    async with context.start(action="helm_dry_run") as ctx:
        cmd = (
            f"helm upgrade --dry-run --install {release_name} --create-namespace --namespace {namespace} "
            + f" --values {str(values_file)} {str(chart_folder)} {args}"
        )
        return_code, outputs = await execute_shell_cmd(cmd, ctx)

    return return_code, cmd, outputs


async def helm_install(
    release_name: str,
    kube_context: str,
    namespace: str,
    values_file: Path,
    chart_folder: Path,
    context: Context,
    timeout=120,
    args="",
):
    return await helm_install_or_upgrade(
        release_name=release_name,
        namespace=namespace,
        values_file=values_file,
        kube_context=kube_context,
        chart_folder=chart_folder,
        timeout=timeout,
        args=args,
        context=context,
    )


async def helm_upgrade(
    release_name: str,
    kube_context: str,
    namespace: str,
    values_file: Path,
    chart_folder: Path,
    context: Context,
    timeout=120,
    args="",
):
    return await helm_install_or_upgrade(
        release_name=release_name,
        namespace=namespace,
        values_file=values_file,
        kube_context=kube_context,
        chart_folder=chart_folder,
        timeout=timeout,
        args=args,
        context=context,
    )


async def helm_uninstall(
    release_name: str,
    kube_context: str,
    namespace: str,
    context: Context,
):
    cmd = f"helm uninstall --namespace {namespace} --kube-context {kube_context} {release_name}"
    await context.info(text=cmd)
    await execute_shell_cmd(cmd, context)


async def helm_install_or_upgrade(
    release_name: str,
    namespace: str,
    values_file: Path,
    chart_folder: Path,
    kube_context: str,
    context: Context,
    timeout=120,
    args="",
):
    async with context.start(action="helm_install_or_upgrade") as ctx:
        cmd = (
            f"helm upgrade --install {release_name} --create-namespace --namespace {namespace} "
            + f"--kube-context {kube_context} --values {str(values_file)} --atomic "
            f"--timeout {timeout}s {str(chart_folder)} {args}"
        )
        return_code, outputs = await execute_shell_cmd(cmd, ctx)

    return return_code, cmd, outputs
