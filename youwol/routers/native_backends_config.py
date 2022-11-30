import youwol_accounts
import youwol_assets_backend as assets_backend
import youwol_assets_gateway as assets_gtw
import youwol_cdn_apps_server as cdn_apps_server
import youwol_cdn_backend as cdn
import youwol_cdn_sessions_storage as cdn_sessions_storage
import youwol_files_backend as youwol_files_backend
import youwol_flux_backend as flux_backend
import youwol_mock_backend as mock_backend
import youwol_stories_backend as stories
import youwol_tree_db_backend as tree_db
from youwol.environment.clients import LocalClients
from youwol.environment.youwol_environment import yw_config
from youwol_stories_backend import Configuration as StoriesConfig
from youwol_utils import CdnClient, CacheClient
from youwol_utils.clients.assets.assets import AssetsClient
from youwol_utils.clients.docdb.local_docdb import LocalDocDbClient as LocalDocDb, LocalDocDbClient
from youwol_utils.clients.file_system.local_file_system import LocalFileSystem
from youwol_utils.clients.files import FilesClient
from youwol_utils.clients.flux.flux import FluxClient
from youwol_utils.clients.storage.local_storage import LocalStorageClient as LocalStorage
from youwol_utils.clients.stories.stories import StoriesClient
from youwol_utils.clients.treedb.treedb import TreeDbClient
from youwol_utils.context import ContextFactory
from youwol_utils.http_clients.assets_backend import ASSETS_TABLE, ACCESS_HISTORY, ACCESS_POLICY
from youwol_utils.http_clients.flux_backend import PROJECTS_TABLE, COMPONENTS_TABLE
from youwol_utils.http_clients.tree_db_backend import create_doc_dbs


async def cdn_config_py_youwol():
    env = await yw_config()
    return cdn.Configuration(
        file_system=LocalFileSystem(
            root_path=env.pathsBook.local_storage / cdn.Constants.namespace / 'youwol-users'
        ),
        doc_db=LocalDocDb(root_path=env.pathsBook.local_docdb,
                          keyspace_name=cdn.Constants.namespace,
                          table_body=cdn.Constants.schema_docdb)
    )


async def tree_db_config_py_youwol():
    env = await yw_config()
    doc_dbs = create_doc_dbs(
        factory_db=LocalDocDbClient,
        root_path=env.pathsBook.local_docdb
    )
    return tree_db.Configuration(
        doc_dbs=doc_dbs
    )


async def assets_backend_config_py_youwol():
    env = await yw_config()
    return assets_backend.Configuration(
        storage=LocalStorage(
            root_path=env.pathsBook.local_storage,
            bucket_name=assets_backend.Constants.namespace
        ),
        doc_db_asset=LocalDocDb(
            root_path=env.pathsBook.local_docdb,
            keyspace_name=assets_backend.Constants.namespace,
            table_body=ASSETS_TABLE
        ),
        doc_db_access_history=LocalDocDb(
            root_path=env.pathsBook.local_docdb,
            keyspace_name=assets_backend.Constants.namespace,
            table_body=ACCESS_HISTORY
        ),
        doc_db_access_policy=LocalDocDbClient(
            root_path=env.pathsBook.local_docdb,
            keyspace_name=assets_backend.Constants.namespace,
            table_body=ACCESS_POLICY
        )
    )


async def flux_backend_config_py_youwol():
    env = await yw_config()
    return flux_backend.Configuration(
        storage=LocalStorage(root_path=env.pathsBook.local_storage,
                             bucket_name=flux_backend.Constants.namespace),
        doc_db=LocalDocDbClient(root_path=env.pathsBook.local_docdb,
                                keyspace_name=flux_backend.Constants.namespace,
                                table_body=PROJECTS_TABLE
                                ),
        doc_db_component=LocalDocDbClient(
            root_path=env.pathsBook.local_docdb,
            keyspace_name=flux_backend.Constants.namespace,
            table_body=COMPONENTS_TABLE
        ),
        assets_gtw_client=LocalClients.get_assets_gateway_client(env=env),
        cdn_client=LocalClients.get_cdn_client(env=env)
    )


async def assets_gtw_config_py_youwol():
    env = await yw_config()
    url_base = f"http://localhost:{env.httpPort}/api"

    config_yw_assets_gateway = assets_gtw.Configuration(
        flux_client=FluxClient(url_base=f"{url_base}/flux-backend"),
        cdn_client=CdnClient(url_base=f"{url_base}/cdn-backend"),
        stories_client=StoriesClient(url_base=f"{url_base}/stories-backend"),
        treedb_client=TreeDbClient(url_base=f"{url_base}/treedb-backend"),
        assets_client=AssetsClient(url_base=f"{url_base}/assets-backend"),
        files_client=FilesClient(url_base=f"{url_base}/files-backend")
    )

    return config_yw_assets_gateway


async def stories_config_py_youwol():
    env = await yw_config()
    return StoriesConfig(
        storage=LocalStorage(
            root_path=env.pathsBook.local_storage,
            bucket_name=stories.Constants.namespace
        ),
        doc_db_stories=LocalDocDb(
            root_path=env.pathsBook.local_docdb,
            keyspace_name=stories.Constants.namespace,
            table_body=stories.Constants.db_schema_stories
        ),
        doc_db_documents=LocalDocDb(
            root_path=env.pathsBook.local_docdb,
            keyspace_name=stories.Constants.namespace,
            table_body=stories.Constants.db_schema_documents,
            secondary_indexes=[stories.Constants.db_schema_doc_by_id]
        ),
        assets_gtw_client=LocalClients.get_assets_gateway_client(env=env)
    )


async def cdn_apps_server_config_py_youwol():
    env = await yw_config()
    return cdn_apps_server.Configuration(
        assets_gtw_client=LocalClients.get_assets_gateway_client(env=env)
    )


async def cdn_session_storage_config_py_youwol():
    env = await yw_config()
    return cdn_sessions_storage.Configuration(
        storage=LocalStorage(
            root_path=env.pathsBook.local_storage,
            bucket_name=cdn_sessions_storage.Constants.namespace
        ),
    )


async def files_backend_config_py_youwol():
    env = await yw_config()
    bucket_name = youwol_files_backend.Constants.namespace

    return youwol_files_backend.Configuration(
        file_system=LocalFileSystem(
            root_path=env.pathsBook.local_storage / bucket_name / 'youwol-users'
        ),
    )


async def accounts_backend_config_py_youwol():
    config = await yw_config()
    pkce_cache: CacheClient = ContextFactory.with_static_data['accounts_pkce_cache']
    jwt_cache: CacheClient = ContextFactory.with_static_data['jwt_cache']
    return youwol_accounts.Configuration(
        openid_base_url=config.get_remote_info().authProvider.openidBaseUrl,
        openid_client=config.get_remote_info().authProvider.openidClient,
        admin_client=config.get_remote_info().authProvider.keycloakAdminClient,
        keycloak_admin_base_url=config.get_remote_info().authProvider.keycloakAdminBaseUrl,
        jwt_cache=jwt_cache,
        pkce_cache=pkce_cache
    )


async def mock_backend_config_py_youwol():
    await yw_config()
    return mock_backend.Configuration()
