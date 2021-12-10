import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from configuration import YouwolConfiguration
from configuration.clients import RemoteClients
from routers.commands.upload_assets.models import UploadTask

from utils_paths import parse_json, write_json
from youwol_utils import JSON
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient


def zip_local_story(raw_id: str, config: YouwolConfiguration) -> bytes:
    stories = parse_json(config.pathsBook.local_stories_docdb)
    documents = parse_json(config.pathsBook.local_stories_documents_docdb)
    data = {
        "story": next(d for d in stories['documents'] if d['story_id'] == raw_id),
        "documents": [d for d in documents['documents'] if d['story_id'] == raw_id]
        }

    with tempfile.TemporaryDirectory() as tmp_folder:
        base_path = Path(tmp_folder)
        write_json(data=data, path=base_path / 'data.json')
        storage_stories = config.pathsBook.local_stories_storage
        for doc in data['documents']:
            shutil.copy(storage_stories / doc['content_id'], base_path / doc['content_id'])

        zipper = zipfile.ZipFile(base_path / 'story.zip', 'w', zipfile.ZIP_DEFLATED)
        for filename in ['data.json'] + [doc['content_id'] for doc in data['documents']]:
            zipper.write(base_path / filename, arcname=filename)
        zipper.close()
        return (Path(tmp_folder) / "story.zip").read_bytes()


@dataclass
class UploadStoryTask(UploadTask):

    async def get_raw(self) -> bytes:
        zip_content = zip_local_story(raw_id=self.raw_id, config=self.context.config)
        return zip_content

    async def create_raw(self, data: bytes, folder_id: str):

        remote_gtw: AssetsGatewayClient = await RemoteClients.get_assets_gateway_client(context=self.context)
        await remote_gtw.put_asset_with_raw(
            kind='story',
            folder_id=folder_id,
            data={'file': data, 'content_encoding': 'identity'},
            rest_of_path="/publish"
            )

    async def update_raw(self, data: JSON, folder_id: str):
        # <!> stories_client will be removed as it should not be available
        stories_client = await RemoteClients.get_stories_client(context=self.context)
        await stories_client.publish_story(data={'file': data, 'content_encoding': 'identity'})

