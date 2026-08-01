"""Definition of base output plugin."""

import asyncio
from abc import abstractmethod
from collections.abc import Sequence
from typing import TypeVar, assert_never, override

from pydantic import RootModel

from eventum.plugins.base.plugin import Plugin, PluginParams
from eventum.plugins.exceptions import PluginConfigurationError
from eventum.plugins.output.base.config import OutputPluginConfig
from eventum.plugins.output.exceptions import PluginWriteError
from eventum.plugins.output.fields import FormatterConfigT
from eventum.plugins.output.formatters import (
    Formatter,
    FormatterParams,
    FormattingResult,
    get_formatter_class,
)


class OutputPluginParams(PluginParams):
    """Parameters for output plugin."""


ConfigT = TypeVar(
    'ConfigT',
    bound=(OutputPluginConfig | RootModel[OutputPluginConfig]),
)
ParamsT = TypeVar('ParamsT', bound=OutputPluginParams)


class OutputPlugin(Plugin[ConfigT, ParamsT], register=False):
    """Base class for all output plugins."""

    @override
    def __init__(self, config: ConfigT, params: ParamsT) -> None:
        super().__init__(config, params)

        self._loop: asyncio.AbstractEventLoop

        self._is_opened = False

        self._formatter_config = self._get_formatter_config()
        self._formatter = self._get_formatter()

        self._written = 0
        self._format_failed = 0
        self._write_failed = 0

    def _get_formatter_config(self) -> FormatterConfigT:
        """Get formatter config.

        Returns
        -------
        FormatterConfigT
            Formatter config.

        """
        match self._config:
            case OutputPluginConfig():
                return self._config.formatter
            case RootModel():
                return self._config.root.formatter
            case t:
                assert_never(t)

    def _get_formatter(self) -> Formatter:
        """Get formatter corresponding to config.

        Returns
        -------
        Formatter
            Formatter.

        Raises
        ------
        PluginConfigurationError
            If formatter configuration fails.

        """
        config = self._formatter_config
        try:
            FormatterCls = get_formatter_class(config.format)  # noqa: N806
            return FormatterCls(
                config,
                params=FormatterParams(base_path=self._base_path),  # type: ignore[typeddict-item]
            )
        except ValueError as e:
            msg = 'Failed to configure formatter'
            raise PluginConfigurationError(
                msg,
                context={'reason': str(e)},
            ) from None

    async def open(self) -> None:
        """Open plugin for writing.

        Raises
        ------
        PluginOpenError
            If error occurs during opening.

        """
        self._loop = asyncio.get_running_loop()

        if not self._is_opened:
            await self._open()
            self._is_opened = True
            self._written = 0
            self._format_failed = 0
            self._write_failed = 0

        await self._logger.adebug('Plugin is opened for writing')

    async def close(self) -> None:
        """Close plugin for writing with releasing resources and
        flushing events.
        """
        if self._is_opened:
            await self._close()
            self._is_opened = False

        await self._logger.adebug('Plugin is closed')

    async def _format_events(self, events: Sequence[str]) -> FormattingResult:
        """Format events.

        Parameters
        ----------
        events : Sequence[str]
            Events to format.

        Returns
        -------
        FormattingResult
            Formatting result.

        Notes
        -----
        All errors from formatting result are logged.

        """
        formatting_result = await asyncio.to_thread(
            lambda: self._formatter.format_events(events),
        )

        if formatting_result.errors:
            contexts: list[dict] = []

            for error in formatting_result.errors:
                context = {
                    'format': self._formatter_config.format,
                    'reason': str(error),
                }

                if error.original_event is not None:
                    context['original_event'] = error.original_event

                contexts.append(context)

            await asyncio.gather(
                *[
                    self._logger.aerror('Failed to format event', **context)
                    for context in contexts
                ],
            )

        return formatting_result

    async def write(self, events: Sequence[str]) -> int:
        """Write events.

        Parameters
        ----------
        events : Sequence[str]
            Sequence of events to write.

        Returns
        -------
        int
            Number of successfully written events.

        Raises
        ------
        PluginWriteError
            If error occurs during writing events.

        """
        if not events:
            return 0

        if not self._is_opened:
            msg = 'Output plugin is not opened for writing'
            raise PluginWriteError(
                msg,
                context={},
            )

        try:
            formatting_result = await self._format_events(events)
        except:
            self._format_failed += len(events)
            raise

        # count events rejected by formatter, whether individually or
        # as an entire batch by aggregating formatters
        self._format_failed += len(events) - formatting_result.formatted_count

        if not formatting_result.events:
            return 0

        try:
            written = await self._write(formatting_result.events)
        except:
            self._write_failed += formatting_result.formatted_count
            raise

        # handle possible events aggregation
        if (
            len(formatting_result.events) == 1
            and formatting_result.formatted_count > 1
            and written == 1
        ):
            written = formatting_result.formatted_count

        self._written += written
        self._write_failed += max(
            formatting_result.formatted_count - written,
            0,
        )

        return written

    @abstractmethod
    async def _open(self) -> None:
        """Open plugin for writing.

        Notes
        -----
        See `open` method for more info.

        """
        ...

    @abstractmethod
    async def _close(self) -> None:
        """Close plugin for writing with releasing resources and
        flushing events.

        Notes
        -----
        See `close` method for more info.

        """
        ...

    @abstractmethod
    async def _write(self, events: Sequence[str]) -> int:
        """Write events.

        Notes
        -----
        See `write` method for more info.

        Returned number must include only events that reached the
        destination, the rest of them are counted as failed.

        """
        ...

    @property
    def written(self) -> int:
        """Number of written events."""
        return self._written

    @property
    def write_failed(self) -> int:
        """Number of unsuccessfully written events."""
        return self._write_failed

    @property
    def format_failed(self) -> int:
        """Number of unsuccessfully formatted events."""
        return self._format_failed
