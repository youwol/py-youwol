import functools
import itertools
from pathlib import Path

from pydantic.main import BaseModel

from youwol.utils.helm_utils import helm_install, helm_upgrade, helm_list, helm_uninstall
from youwol.utils.k8s_utils import k8s_create_secrets_if_needed
from youwol_utils import to_json
from youwol_utils.context import Context


class K8sPackage(BaseModel):
    name: str
    namespace: str

    async def install(self, context: Context):
        pass

    async def upgrade(self, context: Context):
        pass

    async def is_installed(self, context: Context):
        pass


class HelmPackage(K8sPackage):

    chart_folder: Path
    with_values: dict
    values_filename: str = 'values.yaml'
    secrets: dict = {}
    chart_explorer: dict = {}

    async def before_cmd(self, context: Context):
        await k8s_create_secrets_if_needed(namespace=self.namespace, secrets=self.secrets, context=context)

    async def install(self, context: Context):

        async with context.start(action='install helm package') as ctx:
            await self.before_cmd(context=ctx)
            keys = HelmPackage.flatten_schema_values(self.with_values)
            args = functools.reduce(lambda acc, e: acc + f"--set {e[1:]} ", keys, "")
            return await helm_install(
                release_name=self.name,
                namespace=self.namespace,
                values_file=self.chart_folder / self.values_filename,
                chart_folder=Path(self.chart_folder),
                timeout=240,
                args=args,
                context=ctx)

    async def upgrade(self, context: Context):

        async with context.start(action='upgrade helm package') as ctx:
            await self.before_cmd(context=ctx)
            keys = HelmPackage.flatten_schema_values(self.with_values)
            args = functools.reduce(lambda acc, e: acc + f"--set {e[1:]} ", keys, "")
            return await helm_upgrade(
                release_name=self.name,
                namespace=self.namespace,
                values_file=self.chart_folder / self.values_filename,
                chart_folder=Path(self.chart_folder),
                timeout=240,
                args=args,
                context=context
            )

    async def uninstall(self, context: Context):

        async with context.start(action='uninstall helm package') as ctx:
            await self.before_cmd(context=ctx)
            return await helm_uninstall(release_name=self.name, namespace=self.namespace, context=ctx)

    async def is_installed(self, context: Context):
        charts = await helm_list(namespace=self.namespace, selector=None, context=context)
        context.info(text="List of installed packages", data={"charts": [to_json(c) for c in charts]})
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
