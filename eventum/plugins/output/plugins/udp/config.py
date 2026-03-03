"""Definition of udp output plugin config."""

from pydantic import Field

from eventum.plugins.fields import Encoding
from eventum.plugins.output.base.config import OutputPluginConfig


class UdpOutputPluginConfig(OutputPluginConfig, frozen=True):
    r"""Configuration for `udp` output plugin.

    Attributes
    ----------
    host : str
        Hostname or IP address to send datagrams to.

    port : int
        UDP port number to send datagrams to.

    encoding : Encoding, default='utf_8'
        Encoding used to encode events before sending.

    separator : str, default='\\n'
        Separator appended after each event.

    """

    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    encoding: Encoding = Field(default='utf_8')
    separator: str = Field(default='\n')
