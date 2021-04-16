import asyncio
import itertools
from typing import Optional

from aiohttp import FormData
from fastapi import FastAPI, Depends, Header
import uvicorn

from configurations import get_configuration, Configuration
from models import GetRawResp, PostDataBody, PostDataResp

flatten = itertools.chain.from_iterable


configuration = asyncio.get_event_loop().run_until_complete(get_configuration())


app = FastAPI(
    title="{{name}}",
    description="{{description}}",
    root_path="/api/{{name}}"
    )


@app.get(configuration.base_path + "/healthz")
async def healthz():
    return {"status": "tutu listening"}


@app.get(
    configuration.base_path + "/data/{raw_id}",
    summary="Get data from the assets store.",
    response_model=GetRawResp
    )
async def get_data_example(
        raw_id: str,
        authorization: Optional[str] = Header(None),
        conf: Configuration = Depends(get_configuration)
        ):
    content = await conf.assets_client.get_raw(
        kind='data',
        raw_id=raw_id,
        headers={'authorization': authorization} if authorization else {}
        )
    return GetRawResp(rawId=raw_id, content=content)


@app.post(
    configuration.base_path + "/data",
    summary="Post data to the assets store.",
    response_model=PostDataResp
    )
async def post_data_example(
        body: PostDataBody,
        authorization: Optional[str] = Header(None),
        conf: Configuration = Depends(get_configuration),
        ):
    form_data = FormData()
    form_data.add_field('file', body.content, filename=body.fileName, content_type='text/plain')
    resp = await conf.assets_client.put_asset_with_raw(
        kind='data',
        folder_id=body.folderId,
        data=form_data,
        headers={'authorization': authorization} if authorization else {}
        )
    return PostDataResp(**resp)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=configuration.port)
