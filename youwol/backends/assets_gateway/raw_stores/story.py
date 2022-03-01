import json
from dataclasses import dataclass
from typing import Union

from starlette.requests import Request

from .interface import (RawStore, RawId, AssetMeta)


@dataclass(frozen=True)
class StoriesStore(RawStore):
    path_name = 'story'

    async def create_asset(self, request: Request, metadata: AssetMeta, rest_of_path: str, headers) -> \
            (RawId, AssetMeta):

        if rest_of_path == "publish":
            form = await request.form()
            form = {
                'file': await form.get('file').read(),
                'content_encoding': form.get('content_encoding', 'identity')
            }
            resp = await self.client.publish_story(data=form, headers=headers)
            return resp['storyId'], AssetMeta(name=resp['title'])

        body = await request.body()
        body = json.loads(body.decode('utf8')) if body else None

        if body is None:
            body = {
                "title": metadata.name
            }

        resp = await self.client.create_story(body=body, headers=headers)
        return resp['storyId'], AssetMeta(name=resp['title'])

    async def sync_asset_metadata(self, request: Request, raw_id: str, metadata: AssetMeta, headers):

        await self.client.update_story(
            story_id=raw_id,
            body={"title": metadata.name},
            headers=headers
        )

    async def get_asset_metadata(self, request: Request, raw_id: str, rest_of_path: Union[str, None], headers):
        raise NotImplementedError("StoriesStore@get_asset_metadata: endpoint not found")

    async def update_asset(self, request: Request, raw_id: str, metadata: AssetMeta, rest_of_path: str, headers):

        if rest_of_path.startswith('contents/'):
            # POST a new content
            body = await request.body()
            body = json.loads(body.decode('utf8'))
            content_id = rest_of_path.split('/')[1]
            return await self.client.set_content(story_id=raw_id, content_id=content_id, body=body, headers=headers)

        if rest_of_path == 'documents':
            # PUT a document
            body = await request.body()
            body = json.loads(body.decode('utf8'))
            return await self.client.create_document(story_id=raw_id, body=body, headers=headers)

        if rest_of_path.endswith('delete'):
            # DELETE a document
            document_id = rest_of_path.split('/')[1]
            return await self.client.delete_document(story_id=raw_id, document_id=document_id, headers=headers)

        if rest_of_path.startswith("documents/"):
            # POST a document
            document_id = rest_of_path.split('/')[1]
            body = await request.body()
            body = json.loads(body.decode('utf8'))
            return await self.client.update_document(story_id=raw_id, document_id=document_id, body=body,
                                                     headers=headers)

        if rest_of_path.startswith("plugins"):
            # POST a plugin
            body = await request.body()
            body = json.loads(body.decode('utf8'))
            return await self.client.add_plugin(story_id=raw_id, body=body, headers=headers)

        raise NotImplementedError("StoriesStore@update_asset")

    async def get_asset(self, request: Request, raw_id: str, rest_of_path: Union[str, None], headers):

        if not rest_of_path:
            return await self.client.get_story(story_id=raw_id, headers=headers)

        if rest_of_path.endswith('/children'):
            parent_document_id = rest_of_path.split('/')[1]
            from_index = request.query_params.get('from-index')
            count = request.query_params.get('count')
            return await self.client.get_children(story_id=raw_id, parent_document_id=parent_document_id,
                                                  from_index=from_index, count=count, headers=headers)

        if rest_of_path.startswith('contents/'):
            content_id = rest_of_path.split('/')[1]
            return await self.client.get_content(story_id=raw_id, content_id=content_id, headers=headers)

        raise NotImplementedError("StoriesStore@get_asset: endpoint not found")

    async def delete_asset(self, request: Request, raw_id, headers):

        await self.client.delete_story(story_id=raw_id, headers=headers)
