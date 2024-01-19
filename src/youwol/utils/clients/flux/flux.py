# standard library
from dataclasses import dataclass

# typing
from typing import Optional

# Youwol utilities
from youwol.utils.clients.request_executor import (
    RequestExecutor,
    bytes_reader,
    json_reader,
)


@dataclass(frozen=True)
class FluxClient:
    url_base: str

    request_executor: RequestExecutor

    async def get_projects(self, **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/projects",
            default_reader=json_reader,
            **kwargs,
        )

    async def create_project(self, body, **kwargs):
        return await self.request_executor.post(
            url=f"{self.url_base}/projects/create",
            default_reader=json_reader,
            json=body,
            **kwargs,
        )

    async def upload_project(self, data, project_id: Optional[str] = None, **kwargs):
        params = kwargs["params"] if "params" in kwargs else {}
        params = {**params, "project-id": project_id} if project_id else params
        kwargs["params"] = params

        return await self.request_executor.post(
            url=f"{self.url_base}/projects/upload",
            default_reader=json_reader,
            data=data,
            **kwargs,
        )

    async def download_zip(self, project_id: Optional[str] = None, **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/projects/{project_id}/download-zip",
            default_reader=bytes_reader,
            **kwargs,
        )

    async def update_project(self, project_id, body, **kwargs):
        return await self.request_executor.post(
            url=f"{self.url_base}/projects/{project_id}",
            json=body,
            default_reader=json_reader,
            **kwargs,
        )

    async def get_project(self, project_id: str, **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/projects/{project_id}",
            default_reader=json_reader,
            **kwargs,
        )

    async def delete_project(self, project_id: str, **kwargs):
        return await self.request_executor.delete(
            url=f"{self.url_base}/projects/{project_id}",
            default_reader=json_reader,
            **kwargs,
        )

    async def get_records(self, body, **kwargs):
        return await self.request_executor.post(
            url=f"{self.url_base}/records",
            default_reader=json_reader,
            json=body,
            **kwargs,
        )

    async def update_metadata(self, project_id: str, body, **kwargs):
        return await self.request_executor.post(
            url=f"{self.url_base}/projects/{project_id}/metadata",
            default_reader=json_reader,
            json=body,
            **kwargs,
        )

    async def get_metadata(self, project_id: str, **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/projects/{project_id}/metadata",
            default_reader=json_reader,
            **kwargs,
        )

    async def duplicate(self, project_id: str, **kwargs):
        return await self.request_executor.post(
            url=f"{self.url_base}/projects/{project_id}/duplicate",
            default_reader=json_reader,
            **kwargs,
        )

    async def publish_application(self, project_id: str, body, **kwargs):
        return await self.request_executor.post(
            url=f"{self.url_base}/projects/{project_id}/publish-application",
            json=body,
            default_reader=json_reader,
            **kwargs,
        )
