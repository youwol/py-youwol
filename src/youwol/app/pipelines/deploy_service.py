# standard library
import functools
import itertools

from pathlib import Path

# typing
from typing import List

# third parties
from pydantic import BaseModel

# Youwol utilities
from youwol.utils import to_json
from youwol.utils.context import Context
from youwol.utils.utils_helm import (
    helm_dry_run,
    helm_install,
    helm_list,
    helm_uninstall,
)


class K8sPackage(BaseModel):
    name: str
    namespace: str

    async def install(self, kube_context: str, context: Context):
        raise NotImplementedError()

    async def upgrade(self, kube_context: str, context: Context):
        raise NotImplementedError()

    async def is_installed(self, kube_context: str, context: Context):
        raise NotImplementedError()


class HelmPackage(K8sPackage):
    chart_folder: Path
    with_values: dict
    values_filename: str = "values.yaml"
    secrets: List[Path] = []
    chart_explorer: dict = {}

    async def dry_run(self, context: Context):
        async with context.start(action="dry run install helm package") as ctx:
            keys = HelmPackage.flatten_schema_values(self.with_values)
            args = functools.reduce(lambda acc, e: acc + f"--set {e[1:]} ", keys, "")
            return await helm_dry_run(
                release_name=self.name,
                namespace=self.namespace,
                values_file=self.chart_folder / self.values_filename,
                chart_folder=Path(self.chart_folder),
                args=args,
                context=ctx,
            )

    async def install_or_upgrade(self, kube_context: str, context: Context):
        async with context.start(action="install helm package") as ctx:
            keys = HelmPackage.flatten_schema_values(self.with_values)
            args = functools.reduce(lambda acc, e: acc + f"--set {e[1:]} ", keys, "")
            return await helm_install(
                release_name=self.name,
                namespace=self.namespace,
                kube_context=kube_context,
                values_file=self.chart_folder / self.values_filename,
                chart_folder=Path(self.chart_folder),
                timeout=240,
                args=args,
                context=ctx,
            )

    async def install(self, kube_context: str, context: Context):
        return await self.install_or_upgrade(kube_context=kube_context, context=context)

    async def upgrade(self, kube_context: str, context: Context):
        return await self.install_or_upgrade(kube_context=kube_context, context=context)

    async def uninstall(self, kube_context: str, context: Context):
        async with context.start(action="uninstall helm package") as ctx:
            return await helm_uninstall(
                release_name=self.name,
                kube_context=kube_context,
                namespace=self.namespace,
                context=ctx,
            )

    async def is_installed(self, kube_context: str, context: Context):
        charts = await helm_list(
            namespace=self.namespace,
            kube_context=kube_context,
            selector=None,
            context=context,
        )
        await context.info(
            text="List of installed packages",
            data={"charts": [to_json(c) for c in charts]},
        )
        return self.name in [r.name for r in charts]

    @staticmethod
    def flatten_schema_values(dict_object: dict, prefix=""):
        r = []
        for k, v in dict_object.items():
            if isinstance(v, dict):
                r.append(HelmPackage.flatten_schema_values(v, prefix + "." + k))
            else:
                r.append([prefix + "." + k + "=" + str(v)])
        return list(itertools.chain.from_iterable(r))
