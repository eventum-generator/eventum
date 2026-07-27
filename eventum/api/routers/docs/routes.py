"""Routes."""

from pathlib import Path

import aiofiles
from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import HTMLResponse

from eventum.api.dependencies.app import AsyncapiSchemaDep

router = APIRouter()


BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / 'static'
ASYNCAPI_PAGE_PATH = STATIC_DIR / 'asyncapi.html'


@router.get('/asyncapi.yml', include_in_schema=False)
async def get_asyncapi_spec(schema: AsyncapiSchemaDep) -> Response:
    return Response(content=schema, media_type='text/plain')


@router.get('/asyncapi', include_in_schema=False)
async def get_asyncapi_html() -> HTMLResponse:
    try:
        async with aiofiles.open(ASYNCAPI_PAGE_PATH) as f:
            return HTMLResponse(await f.read())
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Cannot open HTML document file due to OS error: {e}',
        ) from None
