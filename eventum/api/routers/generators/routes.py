"""Routes."""

import asyncio
from datetime import datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Body,
    HTTPException,
    Path,
    Query,
    WebSocket,
    WebSocketException,
    status,
)

from eventum.api.dependencies.app import (
    GeneratorManagerDep,
    SettingsDep,
    StartupDep,
)
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
    QueuesStats,
    QueueStats,
    RenameGeneratorRequest,
    ResourcesStats,
)
from eventum.api.utils.log_streaming import stream_log_file_to_websocket
from eventum.api.utils.response_description import merge_responses
from eventum.api.utils.websocket_annotations import (
    AsyncAPIMessage,
    Receives,
    Rejects,
)
from eventum.app.manager import GeneratorManager, ManagingError
from eventum.app.renaming import (
    RenameBlockedError,
    RenameConflictError,
    RenameError,
    RenameNotFoundError,
    rename_instance,
)
from eventum.core.generator import Generator
from eventum.core.parameters import GeneratorParameters
from eventum.core.resources import ThreadCpuTimes, sample_thread_cpu_times
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
            try:
                params = generator.params.as_relative(
                    base_dir=settings.path.generators_dir,
                )
            except ValueError:
                params = generator.params

            generators_info.append(
                GeneratorInfo(
                    id=generator_id,
                    path=params.path,
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
    '/{id}/rename',
    description=(
        'Rename generator. The definition in the startup file is renamed '
        'along with the generator, and scenario membership is kept.'
    ),
    responses=merge_responses(
        {404: {'description': 'Generator with provided id is not found'}},
        {
            409: {
                'description': (
                    'Generator with the new id already exists, or the '
                    'generator is active'
                ),
            },
            500: {
                'description': (
                    'Startup file cannot be read, validated, or written'
                ),
            },
        },
    ),
)
async def rename_generator(
    id: Annotated[str, Path(description='Generator id', min_length=1)],
    request: Annotated[
        RenameGeneratorRequest,
        Body(description='New generator id'),
    ],
    generator_manager: GeneratorManagerDep,
    startup: StartupDep,
) -> None:
    try:
        await asyncio.to_thread(
            lambda: rename_instance(
                manager=generator_manager,
                startup=startup,
                id=id,
                new_id=request.new_id,
            ),
        )
    except RenameNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from None
    except (RenameConflictError, RenameBlockedError) as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from None
    except RenameError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from None


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


def _build_stats(
    generator_id: str,
    generator: Generator,
    start_time: datetime,
    cpu_times: ThreadCpuTimes | None = None,
) -> GeneratorStats:
    """Build stats of a running generator.

    Parameters
    ----------
    generator_id : str
        ID of the generator.

    generator : Generator
        Generator to read the stats from.

    start_time : datetime
        Start time of the generator.

    cpu_times : ThreadCpuTimes | None, default=None
        Already sampled CPU times of the process threads to read from
        instead of sampling them.

    Returns
    -------
    GeneratorStats
        Stats of the generator.

    Raises
    ------
    RuntimeError
        If the generator stopped executing, so its runtime information
        is gone.

    """
    plugins = generator.get_plugins_info()
    resources = generator.get_resources(cpu_times)

    return GeneratorStats(
        id=generator_id,
        start_time=start_time,
        resources=ResourcesStats(
            thread_count=resources.thread_count,
            cpu_seconds=resources.cpu_seconds,
            run_delay_seconds=resources.run_delay_seconds,
            disk_read_bytes=resources.disk_read_bytes,
            disk_written_bytes=resources.disk_written_bytes,
            network_sent_bytes=resources.network_sent_bytes,
            network_received_bytes=resources.network_received_bytes,
            queues=QueuesStats(
                timestamps=QueueStats(
                    size=resources.queues.timestamps.size,
                    maxsize=resources.queues.timestamps.maxsize,
                ),
                events=QueueStats(
                    size=resources.queues.events.size,
                    maxsize=resources.queues.events.maxsize,
                ),
            ),
        ),
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
            dropped=plugins.event.dropped,
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


def _collect_running_stats(
    generator_manager: GeneratorManager,
) -> list[GeneratorStats]:
    """Build stats of every running generator.

    Parameters
    ----------
    generator_manager : GeneratorManager
        Manager holding the generators.

    Returns
    -------
    list[GeneratorStats]
        Stats of the generators that are running.

    Notes
    -----
    CPU times of the process threads are sampled once for all of the
    generators, since reading them costs the same however many are
    accounted for. A generator that is removed or stops while its stats
    are being built is left out instead of failing the whole response.

    """
    cpu_times = sample_thread_cpu_times()
    stats: list[GeneratorStats] = []

    for generator_id in generator_manager.generator_ids:
        try:
            generator = generator_manager.get_generator(generator_id)
        except ManagingError:
            continue

        start_time = generator.start_time

        if not generator.is_running or start_time is None:
            continue

        try:
            stats.append(
                _build_stats(
                    generator_id,
                    generator,
                    start_time,
                    cpu_times,
                ),
            )
        except RuntimeError:
            continue

    return stats


@router.get(
    '/{id}/stats',
    description='Get stats of running generator',
    responses=_get_generator.responses,
)
async def get_generator_stats(
    id: str,
    generator: GeneratorDep,
) -> GeneratorStats:
    start_time = generator.start_time

    if not generator.is_running or start_time is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Generator is not running',
        )

    try:
        return await asyncio.to_thread(
            _build_stats,
            id,
            generator,
            start_time,
        )
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Generator is not running',
        ) from None


@router.get(
    '/group-actions/stats-running',
    description='Get stats of all running generators',
    responses=_get_generator.responses,
)
async def get_running_generators_stats(
    generator_manager: GeneratorManagerDep,
) -> list[GeneratorStats]:
    return await asyncio.to_thread(_collect_running_stats, generator_manager)


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

    await stream_log_file_to_websocket(
        websocket=websocket,
        path=path,
        end_offset=end_offset,
    )
