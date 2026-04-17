"""Definition of replay event plugin."""

import os
import re
from collections.abc import Iterator
from datetime import datetime
from typing import cast, override

from eventum.plugins.event.base.plugin import (
    EventPlugin,
    EventPluginParams,
    ProduceParams,
)
from eventum.plugins.event.exceptions import (
    PluginEventsExhaustedError,
    PluginProduceError,
)
from eventum.plugins.event.plugins.replay.config import ReplayEventPluginConfig
from eventum.plugins.exceptions import PluginConfigurationError


class ReplayEventPlugin(
    EventPlugin[ReplayEventPluginConfig, EventPluginParams],
):
    """Event plugin for producing events using existing log
    file by replaying it line by line.
    """

    @override
    def __init__(
        self,
        config: ReplayEventPluginConfig,
        params: EventPluginParams,
    ) -> None:
        super().__init__(config, params)
        self._filepath = self.resolve_path(self._config.path)

        self._check_file_existence()

        self._pattern = self._initialize_pattern()
        self._lines = self._get_next_line()
        self._last_read_position = 0

    def _check_file_existence(self) -> None:
        """Check if source file exists.

        Raises
        ------
        PluginConfigurationError
            If file does not exist.

        """
        if not self._filepath.exists():
            msg = 'File does not exist'
            raise PluginConfigurationError(
                msg,
                context={'file_path': str(self._filepath)},
            )

    def _initialize_pattern(self) -> re.Pattern | None:
        """Initialize pattern with compiling it if it's provided.

        Returns
        -------
        re.Pattern | None
            Compiled pattern or none.

        Raises
        ------
        PluginConfigurationError
            If pattern compilation fails.

        """
        if self._config.timestamp_pattern is not None:
            try:
                return re.compile(pattern=self._config.timestamp_pattern)
            except re.error as e:
                msg = 'Failed to compile regular expression'
                raise PluginConfigurationError(
                    msg,
                    context={'reason': str(e)},
                ) from None
        else:
            return None

    def _read_next_lines(self, hint: int = 0) -> list[str]:
        """Read next lines from the file.

        Parameters
        ----------
        hint : int, default=0
            Hint can be specified to control the number of lines read:
            no more lines will be read if the total size in bytes of
            all lines so far exceeds hint, by default there is not
            limit.

        Returns
        -------
        list[str]
            Next lines read from the file.

        Raises
        ------
        PluginProduceError
            If error occurs during reading the file.

        """
        self._logger.debug('Reading next lines')
        try:
            with self._filepath.open('rb') as f:
                f.seek(self._last_read_position, os.SEEK_SET)
                byte_lines = f.readlines(hint)
                self._last_read_position = f.tell()
        except OSError as e:
            msg = 'Failed to read file'
            raise PluginProduceError(
                msg,
                context={
                    'reason': str(e),
                    'file_path': str(self._filepath),
                },
            ) from None

        # decode lines in-place to reduce memory usage
        lines = cast('list[str]', byte_lines)

        if not lines:
            self._logger.info(
                'End of file is reached',
                file_path=str(self._filepath),
            )
            return lines

        for i, line in enumerate(byte_lines):
            lines[i] = line.decode(self._config.encoding).rstrip('\n\r')

        self._logger.debug(
            'Next lines from file have been read',
            file_name=self._filepath,
            count=len(lines),
        )
        return lines

    def _get_next_line(self) -> Iterator[str]:
        """Get next line.

        Yields
        ------
        str
            Line.

        Notes
        -----
        Repeating file reading are handled.

        """
        while True:
            while lines := self._read_next_lines(self._config.chunk_size):
                yield from lines

            if not self._config.repeat:
                break
            else:
                self._logger.info(
                    'Reset read position to beginning of the file',
                    file_path=str(self._filepath),
                )

            self._last_read_position = 0

    def _format_timestamp(self, timestamp: datetime) -> str:
        """Format timestamp to specified format.

        Parameters
        ----------
        timestamp : datetime
            Timestamp to format.

        Returns
        -------
        str
            Formatted timestamp.

        """
        if self._config.timestamp_format is None:
            return timestamp.isoformat()
        return timestamp.strftime(
            self._config.timestamp_format,
        )

    def _substitute_string(
        self,
        message: str,
        string: str,
        pattern: re.Pattern,
        group_name: str,
    ) -> str:
        """Substitute string into original message in position defined
        by pattern named group.

        Parameters
        ----------
        message : str
            Original message.

        string : str
            String to substitute.

        pattern : re.Pattern
            Pattern that defines position of substitution.

        group_name : str
            Named group in pattern that defines position of substitution.

        Returns
        -------
        str
            New message with substituted string.

        Raises
        ------
        ValueError
            If substitution is failed.

        """
        msg_match = pattern.search(message)

        if msg_match is None:
            msg = 'No match found'
            raise ValueError(msg)

        try:
            match_start = msg_match.start(group_name)
            match_end = msg_match.end(group_name)
        except IndexError:
            msg = f'No group `{group_name}` found in match'
            raise ValueError(msg) from None

        if match_start == -1 or match_end == -1:
            msg = f'Group `{group_name}` did not contribute to the match'
            raise ValueError(msg)

        return message[:match_start] + string + message[match_end:]

    @override
    def _produce(self, params: ProduceParams) -> list[str]:
        try:
            line = next(self._lines)
        except StopIteration:
            raise PluginEventsExhaustedError from None

        if self._pattern is None:
            return [line]

        fmt_timestamp = self._format_timestamp(timestamp=params['timestamp'])

        try:
            line = self._substitute_string(
                message=line,
                string=fmt_timestamp,
                pattern=self._pattern,
                group_name='timestamp',
            )
        except ValueError as e:
            self._logger.warning(
                'Failed to substitute timestamp into original message',
                reason=str(e),
            )

        return [line]
