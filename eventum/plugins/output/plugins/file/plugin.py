"""Definition of file output plugin."""

import asyncio
import os
from collections.abc import Sequence
from typing import override

import aiofiles
from aiofiles.threadpool.text import AsyncTextIOWrapper

from eventum.plugins.output.base.plugin import OutputPlugin, OutputPluginParams
from eventum.plugins.output.exceptions import PluginOpenError, PluginWriteError
from eventum.plugins.output.plugins.file.config import FileOutputPluginConfig


class FileOutputPlugin(
    OutputPlugin[FileOutputPluginConfig, OutputPluginParams],
):
    """Output plugin for writing events to file."""

    @override
    def __init__(
        self,
        config: FileOutputPluginConfig,
        params: OutputPluginParams,
    ) -> None:
        super().__init__(config, params)

        self._file: AsyncTextIOWrapper

        self._flushing_task: asyncio.Task

        self._cleanup_task: asyncio.Task
        self._cleaned_up = False
        self._cleanup_lock = asyncio.Lock()

        self._filepath = self.resolve_path(self._config.path)

    async def _is_operable(self) -> bool:
        """Check if file is operable (not closed and not deleted).

        Returns
        -------
        bool
            Check result.

        Notes
        -----
        Cleanup lock must be acquired before running this method to
        avoid unexpected file closing when trying to get fileno

        """
        if self._file.closed:
            return False

        fileno = self._file.fileno()

        stat = os.stat(fileno)  # noqa: PTH116

        return stat.st_nlink > 0

    async def _start_flushing(self) -> None:
        """Start flushing cycle based on specified flush interval."""
        if self._config.flush_interval == 0:
            return

        while True:
            await asyncio.sleep(self._config.flush_interval)

            async with self._cleanup_lock:
                if await self._is_operable():
                    await self._file.flush()

    async def _schedule_cleanup(self) -> None:
        """Schedule file closing after specified number of seconds."""
        await asyncio.sleep(self._config.cleanup_interval)

        async with self._cleanup_lock:
            if await self._is_operable():
                await self._file.flush()
                await self._file.close()

            self._cleaned_up = True

        await self._logger.adebug(
            'File is closed',
            file_path=str(self._filepath),
        )

    def _create_descriptor(self, path: str, flags: int) -> int:
        """Create file descriptor opened for writing with specified
        file mode.

        Parameters
        ----------
        path : str
            Path to file.

        flags : int
            Flags for file descriptor.

        Returns
        -------
        int
            File descriptor number.

        """
        return os.open(
            path=path,
            flags=flags,
            mode=int(str(self._config.file_mode), base=8),
        )

    async def _open_file(self) -> AsyncTextIOWrapper:
        """Open file for the first time.

        Returns
        -------
        AsyncTextIOWrapper
            Opened file.

        """
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        f = await aiofiles.open(
            file=self._filepath,
            mode='a' if self._config.write_mode == 'append' else 'w',
            encoding=self._config.encoding,
            opener=self._create_descriptor,
        )
        await self._logger.adebug(
            'File is opened',
            file_path=str(self._filepath),
        )
        return f

    async def _reopen_file(self) -> AsyncTextIOWrapper:
        """Reopen file after deleting or cleanup.

        Returns
        -------
        AsyncTextIOWrapper
            Opened file.

        """
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        f = await aiofiles.open(
            file=self._filepath,
            mode='a',
            encoding=self._config.encoding,
            opener=self._create_descriptor,
        )
        await self._logger.adebug(
            'File is reopened',
            file_path=str(self._filepath),
        )
        return f

    @override
    async def _open(self) -> None:
        try:
            self._file = await self._open_file()
        except OSError as e:
            msg = 'Failed to open file'
            raise PluginOpenError(
                msg,
                context={
                    'reason': str(e),
                    'file_path': str(self._filepath),
                },
            ) from e

        if not await self._file.writable():
            msg = 'File is not writable'
            raise PluginOpenError(
                msg,
                context={
                    'file_path': str(self._filepath),
                },
            )

        self._flushing_task = self._loop.create_task(self._start_flushing())
        self._cleanup_task = self._loop.create_task(self._schedule_cleanup())

    @override
    async def _close(self) -> None:
        self._flushing_task.cancel()
        self._cleanup_task.cancel()

        async with self._cleanup_lock:
            if await self._is_operable():
                await self._file.flush()
                await self._file.close()

    @override
    async def _write(self, events: Sequence[str]) -> int:
        async with self._cleanup_lock:
            if not await self._is_operable():
                if not self._file.closed:
                    await self._file.close()

                try:
                    self._file = await self._reopen_file()
                except OSError as e:
                    msg = 'Failed to reopen file'
                    raise PluginWriteError(
                        msg,
                        context={
                            'reason': str(e),
                            'file_path': str(self._filepath),
                        },
                    ) from e

            if not self._cleaned_up:
                self._cleanup_task.cancel()

            try:
                await self._file.writelines(
                    e + self._config.separator for e in events
                )
            except OSError as e:
                msg = 'Failed to write events to file'
                raise PluginWriteError(
                    msg,
                    context={
                        'reason': str(e),
                        'file_path': str(self._filepath),
                    },
                ) from e
            finally:
                self._cleaned_up = False
                self._cleanup_task = self._loop.create_task(
                    self._schedule_cleanup(),
                )

            if self._config.flush_interval == 0:
                await self._file.flush()

        return len(events)
