"""Routes."""

import asyncio
from typing import Annotated

import aiofiles
import yaml
from fastapi import (
    APIRouter,
    Body,
    HTTPException,
    Query,
    WebSocket,
    WebSocketException,
    status,
)

from eventum.api.dependencies.app import InstanceHooksDep, SettingsDep
from eventum.api.routers.instance.models import InstanceInfo
from eventum.api.utils.log_streaming import stream_log_file_to_websocket
from eventum.api.utils.websocket_annotations import (
    AsyncAPIMessage,
    Receives,
    Rejects,
)
from eventum.app.models.settings import Settings
from eventum.logging.file_paths import construct_main_logfile_path

router = APIRouter()
ws_router = APIRouter()


@router.get('/info', description='Information about app and host')
async def get_info() -> InstanceInfo:
    # InstanceInfo actively uses syscalls that can potentially block event loop
    return await asyncio.to_thread(InstanceInfo)


@router.get(
    '/settings',
    description='Get settings',
    response_description='Current settings of the application',
)
async def get_settings(settings: SettingsDep) -> Settings:
    return settings


@router.put(
    '/settings',
    description=(
        'Update settings. Note that this only updates file. '
        'For changes to take effect u have to restart instance.'
    ),
    responses={
        500: {
            'description': (
                'Error occurred during settings file path resolution'
            ),
        },
    },
)
async def update_settings(
    settings: Annotated[Settings, Body(description='New settings')],
    hooks: InstanceHooksDep,
) -> None:
    try:
        path = await asyncio.to_thread(hooks['get_settings_file_path'])
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Error occurred during settings file path resolution: {e}',
        ) from None

    content = await asyncio.to_thread(
        lambda: yaml.dump(
            settings.model_dump(mode='json', exclude_unset=True),
            sort_keys=False,
        ),
    )

    try:
        async with aiofiles.open(path, 'w') as f:
            await f.write(content)
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Settings cannot be copied due to OS error: {e}',
        ) from None


@router.post(
    '/stop',
    description='Stop instance',
    responses={500: {'description': 'Error occurred during termination'}},
)
async def stop(hooks: InstanceHooksDep) -> None:
    try:
        await asyncio.to_thread(hooks['terminate'])
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Error occurred during termination: {e}',
        ) from None


@router.post(
    '/restart',
    description='Restart instance',
    responses={500: {'description': 'Error occurred during restart'}},
)
async def restart(hooks: InstanceHooksDep) -> None:
    try:
        await asyncio.to_thread(hooks['restart'])
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Error occurred during restart: {e}',
        ) from None


@ws_router.websocket('/logs/main')
async def stream_main_logs(
    settings: SettingsDep,
    websocket: Annotated[
        WebSocket,
        Receives(
            message=AsyncAPIMessage(
                contentType='text/plain',
                name='LogChunk',
                title='Log chunk',
                payload={'type': 'string'},
            ),
        ),
        Rejects(
            status_code=status.WS_1011_INTERNAL_ERROR,
            details='Failed to read log file due to OS error',
        ),
        Rejects(
            status_code=status.WS_1013_TRY_AGAIN_LATER,
            details='Log file does not exist',
        ),
    ],
    end_offset: Annotated[
        int,
        Query(
            ge=0,
            description='Offset from end of file to start reading from',
        ),
    ] = 8192,
) -> None:
    await websocket.accept()

    path = construct_main_logfile_path(
        format=settings.log.format,
        logs_dir=settings.path.logs,
    )

    if not path.exists():
        raise WebSocketException(
            code=status.WS_1013_TRY_AGAIN_LATER,
            reason='Log file does not exist',
        )

    await stream_log_file_to_websocket(
        websocket=websocket,
        path=path,
        end_offset=end_offset,
    )
