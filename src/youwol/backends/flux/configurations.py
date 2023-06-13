# standard library
from dataclasses import dataclass

# typing
from typing import Awaitable, Callable, Dict, Optional

# Youwol utilities
from youwol.utils import CdnClient, DocDb, Storage
from youwol.utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient


@dataclass(frozen=True)
class Constants:
    namespace: str = "flux"

    doc_db_primary_key: str = "project_id"
    doc_db_table_name: str = "projects"

    doc_db_component_primary_key: str = "component_id"
    doc_db_component_table_name: str = "component"

    default_owner: str = "/youwol-users"
    current_schema_version: str = "1"

    @staticmethod
    def workflow_path(base_path):
        return f"{base_path}/workflow.json"

    @staticmethod
    def builder_rendering_path(base_path):
        return f"{base_path}/builderRendering.json"

    @staticmethod
    def runner_rendering_path(base_path):
        return f"{base_path}/runnerRendering.json"

    @staticmethod
    def requirements_path(base_path):
        return f"{base_path}/requirements.json"

    @staticmethod
    def description_path(base_path):
        return f"{base_path}/description.json"


@dataclass(frozen=True)
class Configuration:
    storage: Storage
    doc_db: DocDb
    doc_db_component: DocDb
    assets_gtw_client: AssetsGatewayClient
    cdn_client: CdnClient
    admin_headers: Optional[Dict[str, str]] = None


class Dependencies:
    get_configuration: Callable[[], Awaitable[Configuration]]


async def get_configuration():
    conf = Dependencies.get_configuration()
    if isinstance(conf, Configuration):
        return conf
    return await conf
