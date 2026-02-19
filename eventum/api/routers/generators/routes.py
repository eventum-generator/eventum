"""Routes."""

import asyncio
from typing import Annotated

from fastapi import (
    APIRouter,
    Body,
    HTTPException,
    Path,
    Query,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
    status,
)

from eventum.api.dependencies.app import GeneratorManagerDep, SettingsDep
from eventum.api.routers.generators.dependencies import (
    CheckPathExistsDep,
    GeneratorDep,
    PreparedGeneratorParamsDep,
    check_path_exists,
)
from eventum.api.routers.generators.dependencies import (
    get_generator as _get_generator,
)
from eventum.api.routers.generators.models import (
    BulkStartResponse,
    EventPluginStats,
    GeneratorInfo,
    GeneratorStats,
    GeneratorStatus,
    InputPluginStats,
    OutputPluginStats,
)
from eventum.api.utils.file_streaming import stream_file
from eventum.api.utils.response_description import merge_responses
from eventum.api.utils.websocket_annotations import (
    AsyncAPIMessage,
    Receives,
    Rejects,
)
from eventum.app.manager import ManagingError
from eventum.core.parameters import GeneratorParameters
from eventum.logging.file_paths import construct_generator_logfile_path

router = APIRouter()
ws_router = APIRouter()


@router.get(
    '/',
    description='List ids of all generators',
    response_description='Generators ids',
)
async def list_generators(
    generator_manager: GeneratorManagerDep,
    settings: SettingsDep,
) -> list[GeneratorInfo]:
    generators_info: list[GeneratorInfo] = []
    for generator_id in generator_manager.generator_ids:
        try:
            generator = generator_manager.get_generator(generator_id)
            generators_info.append(
                GeneratorInfo(
                    id=generator_id,
                    path=generator.params.as_relative(
                        base_dir=settings.path.generators_dir,
                    ).path,
                    status=GeneratorStatus(
                        is_initializing=generator.is_initializing,
                        is_running=generator.is_running,
                        is_ended_up=generator.is_ended_up,
                        is_ended_up_successfully=generator.is_ended_up_successfully,
                        is_stopping=generator.is_stopping,
                    ),
                    start_time=generator.start_time,
                ),
            )
        except ManagingError:
            continue

    return generators_info


@router.get(
    '/{id}',
    description='Get generator parameters',
    responses=_get_generator.responses,
)
async def get_generator(
    generator: GeneratorDep,
    settings: SettingsDep,
) -> GeneratorParameters:
    try:
        return generator.params.as_relative(
            base_dir=settings.path.generators_dir,
        )
    except ValueError:
        return generator.params


@router.get(
    '/{id}/status',
    description='Get generator status',
    responses=_get_generator.responses,
)
async def get_generator_status(generator: GeneratorDep) -> GeneratorStatus:
    return GeneratorStatus(
        is_initializing=generator.is_initializing,
        is_running=generator.is_running,
        is_ended_up=generator.is_ended_up,
        is_ended_up_successfully=generator.is_ended_up_successfully,
        is_stopping=generator.is_stopping,
    )


@router.post(
    '/{id}',
    description=(
        'Add generator. Note that `id` path parameter takes precedence '
        'over `id` field in the body.'
    ),
    responses=merge_responses(
        check_path_exists.responses,
        {
            409: {'description': 'Generator with provided id already exists'},
            404: {'description': 'No configuration exists in specified path'},
        },
    ),
    status_code=status.HTTP_201_CREATED,
)
async def add_generator(
    params: Annotated[PreparedGeneratorParamsDep, CheckPathExistsDep],
    generator_manager: GeneratorManagerDep,
) -> None:
    try:
        generator_manager.add(params)
    except ManagingError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from None


@router.put(
    '/{id}',
    description=(
        'Update generator with provided parameters. Note that `id` path '
        'parameter takes precedence over `id` field in the body.'
    ),
    responses=merge_responses(
        _get_generator.responses,
        check_path_exists.responses,
        {
            404: {'description': 'No configuration exists in specified path'},
            400: {'description': 'Generator must be stopped before updating'},
        },
    ),
)
async def update_generator(
    id: Annotated[str, Path(description='Generator id', min_length=1)],
    params: Annotated[PreparedGeneratorParamsDep, CheckPathExistsDep],
    generator_manager: GeneratorManagerDep,
    generator: GeneratorDep,
) -> None:
    if generator.is_initializing or generator.is_running:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Generator must be stopped before updating',
        ) from None

    await asyncio.to_thread(
        lambda: generator_manager.remove(generator_id=id),
    )

    generator_manager.add(params=params)


@router.post(
    '/{id}/start',
    description='Start generator by its id',
    response_description='Working status of generator after start',
    responses={
        404: {'description': 'Generator with provided id is not found'},
    },
)
async def start_generator(
    id: Annotated[str, Path(description='Generator id', min_length=1)],
    generator_manager: GeneratorManagerDep,
) -> bool:
    try:
        return await asyncio.to_thread(lambda: generator_manager.start(id))
    except ManagingError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from None


@router.post(
    '/{id}/stop',
    description='Stop generator by its id',
    responses={
        404: {'description': 'Generator with provided id is not found'},
    },
)
async def stop_generator(
    id: Annotated[str, Path(description='Generator id', min_length=1)],
    generator_manager: GeneratorManagerDep,
) -> None:
    try:
        await asyncio.to_thread(lambda: generator_manager.stop(id))
    except ManagingError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from None


@router.delete(
    '/{id}',
    description='Remove generator by its id. Stop it in case it is running.',
    responses={
        404: {'description': 'Generator with provided id is not found'},
    },
)
async def delete_generator(
    id: Annotated[str, Path(description='Generator id', min_length=1)],
    generator_manager: GeneratorManagerDep,
) -> None:
    try:
        await asyncio.to_thread(lambda: generator_manager.remove(id))
    except ManagingError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from None


@router.get(
    '/{id}/stats',
    description='Get stats of running generator',
    responses=_get_generator.responses,
)
async def get_generator_stats(
    id: str,
    generator: GeneratorDep,
) -> GeneratorStats:
    if generator.is_running and generator.start_time is not None:
        plugins = generator.get_plugins_info()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Generator is not running',
        )

    return GeneratorStats(
        id=id,
        start_time=generator.start_time,
        input=[
            InputPluginStats(
                plugin_name=plugin.name,
                plugin_id=plugin.id,
                generated=plugin.generated,
            )
            for plugin in plugins.input
        ],
        event=EventPluginStats(
            plugin_name=plugins.event.name,
            plugin_id=plugins.event.id,
            produced=plugins.event.produced,
            produce_failed=plugins.event.produce_failed,
        ),
        output=[
            OutputPluginStats(
                plugin_name=plugin.name,
                plugin_id=plugin.id,
                written=plugin.written,
                write_failed=plugin.write_failed,
                format_failed=plugin.format_failed,
            )
            for plugin in plugins.output
        ],
    )


@router.get(
    '/group-actions/stats-running',
    description='Get stats of all running generators',
    responses=_get_generator.responses,
)
async def get_running_generators_stats(
    generator_manager: GeneratorManagerDep,
) -> list[GeneratorStats]:
    stats: list[GeneratorStats] = []

    for generator_id in generator_manager.generator_ids:
        generator = generator_manager.get_generator(generator_id)

        if not generator.is_running or generator.start_time is None:
            continue

        plugins = generator.get_plugins_info()

        stats.append(
            GeneratorStats(
                id=generator_id,
                start_time=generator.start_time,
                input=[
                    InputPluginStats(
                        plugin_name=plugin.name,
                        plugin_id=plugin.id,
                        generated=plugin.generated,
                    )
                    for plugin in plugins.input
                ],
                event=EventPluginStats(
                    plugin_name=plugins.event.name,
                    plugin_id=plugins.event.id,
                    produced=plugins.event.produced,
                    produce_failed=plugins.event.produce_failed,
                ),
                output=[
                    OutputPluginStats(
                        plugin_name=plugin.name,
                        plugin_id=plugin.id,
                        written=plugin.written,
                        write_failed=plugin.write_failed,
                        format_failed=plugin.format_failed,
                    )
                    for plugin in plugins.output
                ],
            ),
        )

    return stats


@router.post(
    '/group-actions/bulk-start',
    description='Bulk start several generators',
    response_description=(
        'Ids of running and non running generators after start. '
        'IDs of not existing generators are just ignored and added to list '
        'of non running generators in the response.'
    ),
)
async def bulk_start_generators(
    ids: Annotated[
        list[str],
        Body(description='Generator IDs to start', min_length=1),
    ],
    generator_manager: GeneratorManagerDep,
) -> BulkStartResponse:
    running_ids, non_running_ids = await asyncio.to_thread(
        lambda: generator_manager.bulk_start(ids),
    )
    return BulkStartResponse(
        running_generator_ids=running_ids,
        non_running_generator_ids=non_running_ids,
    )


@router.post(
    '/group-actions/bulk-stop',
    description='Bulk stop several generators',
)
async def bulk_stop_generators(
    ids: Annotated[
        list[str],
        Body(description='Generator IDs to stop', min_length=1),
    ],
    generator_manager: GeneratorManagerDep,
) -> None:
    await asyncio.to_thread(lambda: generator_manager.bulk_stop(ids))


@router.post(
    '/group-actions/bulk-delete',
    description='Bulk delete several generators',
)
async def bulk_delete_generators(
    ids: Annotated[
        list[str],
        Body(description='Generator IDs to delete', min_length=1),
    ],
    generator_manager: GeneratorManagerDep,
) -> None:
    await asyncio.to_thread(lambda: generator_manager.bulk_remove(ids))


@ws_router.websocket('/{id}/logs')
async def stream_generator_logs(
    id: Annotated[
        str,
        Path(description='ID of the generator whose logs to stream'),
    ],
    settings: SettingsDep,
    generator_manager: GeneratorManagerDep,
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
            status_code=status.WS_1008_POLICY_VIOLATION,
            details='Generator with specified id does not exist',
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

    if id not in generator_manager.generator_ids:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason='Generator with specified id does not exist',
        )

    path = construct_generator_logfile_path(
        format=settings.log.format,
        logs_dir=settings.path.logs,
        generator_id=id,
    )

    if not path.exists():
        raise WebSocketException(
            code=status.WS_1013_TRY_AGAIN_LATER,
            reason='Log file does not exist',
        )

    try:
        async for content in stream_file(path=path, end_offset=end_offset):
            try:
                await websocket.send_text(content)
            except WebSocketDisconnect:
                break
    except OSError as e:
        if websocket.client_state.name == 'CONNECTED':
            raise WebSocketException(
                code=status.WS_1011_INTERNAL_ERROR,
                reason=f'Failed to read log file due to OS error: {e}',
            ) from None
