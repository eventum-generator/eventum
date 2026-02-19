"""Definition of stdout output plugin config."""

import os
from typing import Literal

from pydantic import Field

from eventum.plugins.fields import Encoding
from eventum.plugins.output.base.config import OutputPluginConfig


class StdoutOutputPluginConfig(OutputPluginConfig, frozen=True):
    """Configuration for `stdout` output plugin.

    Attributes
    ----------
    flush_interval : float, default=1
        Interval (in seconds) of events flushing, if value is set to 0
        then flush is performed for every event.

    stream : Literal['stdout', 'stderr'], default='stdout'
        Stream to write events in.

    encoding : Encoding, default='utf-8'
        Encoding.

    separator : str, default=os.linesep
        Separator between events.

    """

    flush_interval: float = Field(default=1, ge=0)
    stream: Literal['stdout', 'stderr'] = 'stdout'
    encoding: Encoding = Field(default='utf_8')
    separator: str = Field(default=os.linesep)
