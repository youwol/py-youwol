from typing import Callable, Optional

from dataclasses import dataclass

from youwol.environment.youwol_environment import yw_config, YouwolEnvironment
from youwol_utils import (
    LocalDocDbClient, LocalStorageClient
    )
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from .models import PROJECTS_TABLE, COMPONENTS_TABLE

from youwol.configurations import api_configuration as py_yw_config


@dataclass(frozen=True)
class Configuration:

    yw_config: YouwolEnvironment
    open_api_prefix: str
    base_path: str
    storage: LocalStorageClient
    doc_db: LocalDocDbClient
    doc_db_component: LocalDocDbClient
    assets_gtw_client: AssetsGatewayClient

    namespace: str = "flux"

    doc_db_primary_key: str = "project_id"
    doc_db_table_name: str = "projects"

    doc_db_component_primary_key: str = "component_id"
    doc_db_component_table_name: str = "component"

    cache_prefix: str = "flux-backend_"

    unprotected_paths: Callable[[str], bool] = lambda url: \
        url.path.split("/")[1] == "healthz" or url.path.split("/")[1] == "openapi-docs"

    replication_factor: int = 2
    admin_headers = None
    default_owner = "/youwol-users"
    currentSchemaVersion = "1"


config_yw_flux: Optional[Configuration] = None


async def get_configuration(config_yw=None):

    global config_yw_flux
    if not config_yw:
        config_yw = await yw_config()

    if config_yw_flux and config_yw_flux.yw_config == config_yw:
        return config_yw_flux

    storage = LocalStorageClient(root_path=config_yw.pathsBook.local_storage,
                                 bucket_name=Configuration.namespace)

    doc_db = LocalDocDbClient(root_path=config_yw.pathsBook.local_docdb,
                              keyspace_name=Configuration.namespace,
                              table_body=PROJECTS_TABLE
                              )
    doc_db_component = LocalDocDbClient(
        root_path=config_yw.pathsBook.local_docdb,
        keyspace_name=Configuration.namespace,
        table_body=COMPONENTS_TABLE
        )

    assets_gtw_client = AssetsGatewayClient(url_base=f"http://localhost:{py_yw_config.http_port}/api/assets-gateway")

    config_yw_flux = Configuration(
        yw_config=config_yw,
        open_api_prefix='',
        base_path="/api/flux-backend",
        storage=storage,
        doc_db=doc_db,
        doc_db_component=doc_db_component,
        assets_gtw_client=assets_gtw_client
        )
    return config_yw_flux
