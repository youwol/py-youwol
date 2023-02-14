import json
import shutil
from datetime import datetime
from glob import glob
from pathlib import Path

import youwol_cdn_backend as yw_cdn_backend
import youwol_tree_db_backend as yw_tree_db_backend
import youwol_assets_backend as yw_assets_backend
import youwol_flux_backend as yw_flux_backend
import youwol_assets_gateway as yw_assets_gtw
import youwol_stories_backend as yw_stories_backend
import youwol_cdn_apps_server as yw_cdn_apps_server
import youwol_cdn_sessions_storage as yw_cdn_sessions_storage
import youwol_files_backend as yw_files_backend
import youwol_mock_backend as yw_mock_backend

from youwol_utils import LocalStorageClient, CdnClient
from youwol_utils.clients.assets.assets import AssetsClient
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from youwol_utils.clients.docdb.local_docdb import get_local_nosql_instance
from youwol_utils.clients.file_system.local_file_system import LocalFileSystem
from youwol_utils.clients.files import FilesClient
from youwol_utils.clients.flux.flux import FluxClient
from youwol_utils.clients.stories.stories import StoriesClient
from youwol_utils.clients.treedb.treedb import TreeDbClient
from youwol_utils.http_clients.assets_backend import ASSETS_TABLE, ACCESS_HISTORY, ACCESS_POLICY
from youwol_utils.http_clients.flux_backend import PROJECTS_TABLE, COMPONENTS_TABLE
from youwol_utils.http_clients.tree_db_backend import create_doc_dbs


class BackendConfigurations:

    def __init__(self,
                 assets_backend: yw_assets_backend.Configuration,
                 assets_gtw: yw_assets_gtw.Configuration,
                 cdn_apps_server: yw_cdn_apps_server.Configuration,
                 cdn_backend: yw_cdn_backend.Configuration,
                 files_backend: yw_files_backend.Configuration,
                 cdn_sessions_storage: yw_cdn_sessions_storage.Configuration,
                 flux_backend: yw_flux_backend.Configuration,
                 stories_backend: yw_stories_backend.Configuration,
                 tree_db_backend: yw_tree_db_backend.Configuration,
                 mock_backend: yw_mock_backend.Configuration):
        self.assets_backend = assets_backend
        self.assets_gtw = assets_gtw
        self.cdn_apps_server = cdn_apps_server
        self.cdn_backend = cdn_backend
        self.files_backend = files_backend
        self.cdn_sessions_storage = cdn_sessions_storage
        self.flux_backend = flux_backend
        self.stories_backend = stories_backend
        self.tree_db_backend = tree_db_backend
        self.mock_backend = mock_backend
        self.no_sql_databases = [
            self.assets_backend.doc_db_asset, self.assets_backend.doc_db_access_policy,
            self.assets_backend.doc_db_access_history,
            self.cdn_backend.doc_db,
            self.flux_backend.doc_db, self.flux_backend.doc_db_component,
            self.stories_backend.doc_db_stories, self.stories_backend.doc_db_documents,
            self.tree_db_backend.doc_dbs.items_db, self.tree_db_backend.doc_dbs.folders_db,
            self.tree_db_backend.doc_dbs.drives_db, self.tree_db_backend.doc_dbs.deleted_db
        ]
        self.storage_folders = {
            self.assets_backend.storage.bucket_path, self.assets_backend.file_system.root_path,
            self.cdn_sessions_storage.storage.bucket_path, self.files_backend.file_system.root_path,
            self.cdn_backend.file_system.root_path, self.flux_backend.storage.bucket_path,
            self.stories_backend.storage.bucket_path
        }

    def persist_no_sql_data(self):

        now = datetime.now()
        for database in self.no_sql_databases:
            path = database.data_path
            backup_files = sorted(glob(f"{database.data_path.parent}/backup_*"))
            _ = [Path(f).unlink() for f in backup_files[0:-2]]
            shutil.copyfile(src=database.data_path, dst=database.data_path.parent / f'backup_{now}.json')
            path.write_text(data=json.dumps(database.data, indent=4))

    def reset_databases(self):

        for db in self.no_sql_databases:
            db.data['documents'] = []

        for folder in self.storage_folders:
            shutil.rmtree(folder, ignore_errors=True)


def native_backends_config(
        local_http_port: int,
        local_storage: Path,
        local_nosql: Path
):

    url_base = f"http://localhost:{local_http_port}/api"

    return BackendConfigurations(
        assets_gtw=yw_assets_gtw.Configuration(
            flux_client=FluxClient(url_base=f"{url_base}/flux-backend"),
            cdn_client=CdnClient(url_base=f"{url_base}/cdn-backend"),
            stories_client=StoriesClient(url_base=f"{url_base}/stories-backend"),
            treedb_client=TreeDbClient(url_base=f"{url_base}/treedb-backend"),
            assets_client=AssetsClient(url_base=f"{url_base}/assets-backend"),
            files_client=FilesClient(url_base=f"{url_base}/files-backend")
        ),
        cdn_backend=yw_cdn_backend.Configuration(
            file_system=LocalFileSystem(
                root_path=local_storage / yw_cdn_backend.Constants.namespace / 'youwol-users'
            ),
            doc_db=get_local_nosql_instance(
                root_path=local_nosql,
                keyspace_name=yw_cdn_backend.Constants.namespace,
                table_body=yw_cdn_backend.Constants.schema_docdb,
                secondary_indexes=[])
        ),
        tree_db_backend=yw_tree_db_backend.Configuration(
            doc_dbs=create_doc_dbs(
                factory_db=get_local_nosql_instance,
                root_path=local_nosql
            )
        ),
        assets_backend=yw_assets_backend.Configuration(
            storage=LocalStorageClient(
                root_path=local_storage,
                bucket_name=yw_assets_backend.Constants.namespace
            ),
            doc_db_asset=get_local_nosql_instance(
                root_path=local_nosql,
                keyspace_name=yw_assets_backend.Constants.namespace,
                table_body=ASSETS_TABLE,
                secondary_indexes=[]
            ),
            doc_db_access_history=get_local_nosql_instance(
                root_path=local_nosql,
                keyspace_name=yw_assets_backend.Constants.namespace,
                table_body=ACCESS_HISTORY,
                secondary_indexes=[]
            ),
            doc_db_access_policy=get_local_nosql_instance(
                root_path=local_nosql,
                keyspace_name=yw_assets_backend.Constants.namespace,
                table_body=ACCESS_POLICY,
                secondary_indexes=[]
            ),
            file_system=LocalFileSystem(
                root_path=local_storage / yw_assets_backend.Constants.namespace
            )
        ),
        flux_backend=yw_flux_backend.Configuration(
            storage=LocalStorageClient(
                root_path=local_storage,
                bucket_name=yw_flux_backend.Constants.namespace),
            doc_db=get_local_nosql_instance(
                root_path=local_nosql,
                keyspace_name=yw_flux_backend.Constants.namespace,
                table_body=PROJECTS_TABLE,
                secondary_indexes=[]
            ),
            doc_db_component=get_local_nosql_instance(
                root_path=local_nosql,
                keyspace_name=yw_flux_backend.Constants.namespace,
                table_body=COMPONENTS_TABLE,
                secondary_indexes=[]
            ),
            assets_gtw_client=AssetsGatewayClient(url_base=f"{url_base}/assets-gateway"),
            cdn_client=CdnClient(url_base=f"{url_base}/cdn-backend")
        ),
        stories_backend=yw_stories_backend.Configuration(
            storage=LocalStorageClient(
                root_path=local_storage,
                bucket_name=yw_stories_backend.Constants.namespace
            ),
            doc_db_stories=get_local_nosql_instance(
                root_path=local_nosql,
                keyspace_name=yw_stories_backend.Constants.namespace,
                table_body=yw_stories_backend.Constants.db_schema_stories,
                secondary_indexes=[]
            ),
            doc_db_documents=get_local_nosql_instance(
                root_path=local_nosql,
                keyspace_name=yw_stories_backend.Constants.namespace,
                table_body=yw_stories_backend.Constants.db_schema_documents,
                secondary_indexes=[yw_stories_backend.Constants.db_schema_doc_by_id]
            ),
            assets_gtw_client=AssetsGatewayClient(url_base=f"{url_base}/assets-gateway"),
        ),
        cdn_apps_server=yw_cdn_apps_server.Configuration(
            assets_gtw_client=AssetsGatewayClient(url_base=f"{url_base}/assets-gateway"),
        ),
        cdn_sessions_storage=yw_cdn_sessions_storage.Configuration(
            storage=LocalStorageClient(
                root_path=local_storage,
                bucket_name=yw_cdn_sessions_storage.Constants.namespace
            ),
        ),
        files_backend=yw_files_backend.Configuration(
            file_system=LocalFileSystem(
                root_path=local_storage
            ),
        ),
        mock_backend=yw_mock_backend.Configuration()
    )
