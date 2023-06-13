# standard library
import shutil
import tempfile
import zipfile

from dataclasses import dataclass
from pathlib import Path

# Youwol application
from youwol.app.environment.clients import (
    LocalClients,
    RemoteClients,
    YouwolEnvironment,
)
from youwol.app.routers.environment.upload_assets.models import UploadTask

# Youwol utilities
from youwol.utils import JSON
from youwol.utils.context import Context
from youwol.utils.utils_paths import write_json


def zip_local_story(raw_id: str, config: YouwolEnvironment) -> bytes:
    stories = config.backends_configuration.stories_backend.doc_db_stories.data
    documents = config.backends_configuration.stories_backend.doc_db_documents.data
    data = {
        "story": next(d for d in stories["documents"] if d["story_id"] == raw_id),
        "documents": [d for d in documents["documents"] if d["story_id"] == raw_id],
    }

    with tempfile.TemporaryDirectory() as tmp_folder:
        base_path = Path(tmp_folder)
        write_json(data=data, path=base_path / "data.json")
        storage_stories = config.pathsBook.local_stories_storage
        for doc in data["documents"]:
            shutil.copy(
                storage_stories / doc["content_id"], base_path / doc["content_id"]
            )

        with zipfile.ZipFile(
            base_path / "story.zip", "w", zipfile.ZIP_DEFLATED
        ) as zipper:
            for filename in [
                "data.json",
                *[doc["content_id"] for doc in data["documents"]],
            ]:
                zipper.write(base_path / filename, arcname=filename)
        return (Path(tmp_folder) / "story.zip").read_bytes()


@dataclass
class UploadStoryTask(UploadTask):
    async def get_raw(self, context: Context) -> bytes:
        async with context.start(
            action="UploadPackageTask.get_raw"
        ) as ctx:  # type: Context
            env = await context.get("env", YouwolEnvironment)
            story_client = LocalClients.get_stories_client(env=env)
            zip_content = await story_client.download_zip(
                self.raw_id, headers=ctx.headers()
            )
            return zip_content

    async def create_raw(self, data: bytes, folder_id: str, context: Context):
        async with context.start("UploadStoryTask.create_raw") as ctx:  # type: Context
            remote_gtw = await RemoteClients.get_assets_gateway_client(
                remote_host=self.remote_host
            )
            stories_client = remote_gtw.get_stories_backend_router()
            await stories_client.publish_story(
                data={"file": data, "content_encoding": "identity"},
                params={"folder-id": folder_id},
                headers=ctx.headers(),
            )

    async def update_raw(self, data: JSON, folder_id: str, context: Context):
        # <!> stories_client will be removed as it should not be available
        async with context.start("UploadStoryTask.update_raw") as ctx:  # type: Context
            remote_gtw = await RemoteClients.get_assets_gateway_client(
                remote_host=self.remote_host
            )
            stories_client = remote_gtw.get_stories_backend_router()
            await stories_client.publish_story(
                data={"file": data, "content_encoding": "identity"},
                headers=ctx.headers(),
            )
