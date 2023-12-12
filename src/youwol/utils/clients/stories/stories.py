# standard library
from dataclasses import dataclass

# Youwol utilities
from youwol.utils.clients.request_executor import (
    RequestExecutor,
    bytes_reader,
    json_reader,
    text_reader,
)


@dataclass(frozen=True)
class StoriesClient:
    url_base: str

    request_executor: RequestExecutor

    async def healthz(self, **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/healthz",
            default_reader=json_reader,
            **kwargs,
        )

    async def docs(self, **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/docs",
            default_reader=json_reader,
            **kwargs,
        )

    async def create_story(self, body, **kwargs):
        return await self.request_executor.put(
            url=f"{self.url_base}/stories",
            default_reader=json_reader,
            json=body,
            **kwargs,
        )

    async def publish_story(self, data, **kwargs):
        return await self.request_executor.post(
            url=f"{self.url_base}/stories",
            default_reader=json_reader,
            data=data,
            **kwargs,
        )

    async def download_zip(self, story_id: str, **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/stories/{story_id}/download-zip",
            default_reader=bytes_reader,
            **kwargs,
        )

    async def get_story(self, story_id: str, **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/stories/{story_id}",
            default_reader=json_reader,
            **kwargs,
        )

    async def update_story(self, story_id: str, body, **kwargs):
        return await self.request_executor.post(
            url=f"{self.url_base}/stories/{story_id}",
            default_reader=json_reader,
            json=body,
            **kwargs,
        )

    async def delete_story(self, story_id: str, **kwargs):
        return await self.request_executor.delete(
            url=f"{self.url_base}/stories/{story_id}",
            default_reader=json_reader,
            **kwargs,
        )

    async def get_global_contents(self, story_id: str, **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/stories/{story_id}/global-contents",
            default_reader=json_reader,
            **kwargs,
        )

    async def post_global_contents(self, story_id: str, body, **kwargs):
        return await self.request_executor.post(
            url=f"{self.url_base}/stories/{story_id}/global-contents",
            json=body,
            default_reader=json_reader,
            **kwargs,
        )

    async def get_children(
        self,
        story_id: str,
        parent_document_id: str,
        from_index=float,
        count=int,
        **kwargs,
    ):
        return await self.request_executor.get(
            url=f"{self.url_base}/stories/{story_id}/documents/{parent_document_id}/children",
            params={"from-index": from_index, "count": count},
            default_reader=json_reader,
            **kwargs,
        )

    async def get_content(self, story_id: str, content_id: str, **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/stories/{story_id}/contents/{content_id}",
            default_reader=json_reader,
            **kwargs,
        )

    async def set_content(self, story_id: str, content_id: str, body, **kwargs):
        return await self.request_executor.post(
            url=f"{self.url_base}/stories/{story_id}/contents/{content_id}",
            json=body,
            default_reader=text_reader,
            **kwargs,
        )

    async def get_document(self, story_id: str, document_id: str, **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/stories/{story_id}/documents/{document_id}",
            default_reader=json_reader,
            **kwargs,
        )

    async def create_document(self, story_id: str, body, **kwargs):
        return await self.request_executor.put(
            url=f"{self.url_base}/stories/{story_id}/documents",
            default_reader=json_reader,
            json=body,
            **kwargs,
        )

    async def delete_document(self, story_id: str, document_id: str, **kwargs):
        return await self.request_executor.delete(
            url=f"{self.url_base}/stories/{story_id}/documents/{document_id}",
            default_reader=json_reader,
            **kwargs,
        )

    async def update_document(self, story_id: str, document_id: str, body, **kwargs):
        return await self.request_executor.post(
            url=f"{self.url_base}/stories/{story_id}/documents/{document_id}",
            default_reader=json_reader,
            json=body,
            **kwargs,
        )

    async def move_document(self, story_id: str, document_id: str, body, **kwargs):
        return await self.request_executor.post(
            url=f"{self.url_base}/stories/{story_id}/documents/{document_id}/move",
            default_reader=json_reader,
            json=body,
            **kwargs,
        )

    async def add_plugin(self, story_id: str, body, **kwargs):
        return await self.request_executor.post(
            url=f"{self.url_base}/stories/{story_id}/plugins",
            default_reader=json_reader,
            json=body,
            **kwargs,
        )

    async def upgrade_plugins(self, story_id: str, body, **kwargs):
        return await self.request_executor.post(
            url=f"{self.url_base}/stories/{story_id}/plugins/upgrade",
            default_reader=json_reader,
            json=body,
            **kwargs,
        )
