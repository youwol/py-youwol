from typing import Callable, Optional

from dataclasses import dataclass

from youwol.configuration.youwol_configuration import yw_config, YouwolConfiguration
from youwol_utils import (
    LocalDocDbClient, LocalStorageClient, CdnClient
    )
from .models import PROJECTS_TABLE, COMPONENTS_TABLE

from youwol.configurations import configuration as py_yw_config


@dataclass(frozen=True)
class Configuration:

    yw_config: YouwolConfiguration
    open_api_prefix: str
    base_path: str
    storage: LocalStorageClient
    doc_db: LocalDocDbClient
    doc_db_component: LocalDocDbClient
    cdn_client: CdnClient

    namespace: str = "flux"

    doc_db_primary_key: str = "project_id"
    doc_db_table_name: str = "projects"

    doc_db_component_primary_key: str = "component_id"
    doc_db_component_table_name: str = "component"

    cache_prefix: str = "flux-backend_"

    unprotected_paths: Callable[[str], bool] = lambda url: \
        url.path.split("/")[1] == "healthz" or url.path.split("/")[1] == "openapidocs"

    replication_factor: int = 2

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

    cdn_client = CdnClient(url_base=f"http://localhost:{py_yw_config.http_port}/api/cdn-backend")

    config_yw_flux = Configuration(
        yw_config=config_yw,
        open_api_prefix='',
        base_path="/api/flux-backend",
        storage=storage,
        doc_db=doc_db,
        doc_db_component=doc_db_component,
        cdn_client=cdn_client
        )
    return config_yw_flux
