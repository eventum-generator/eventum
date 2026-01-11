"""Model for the main settings of the application."""

from pydantic import BaseModel

from eventum.app.models.parameters.log import LogParameters
from eventum.app.models.parameters.path import PathParameters
from eventum.app.models.parameters.server import ServerParameters
from eventum.core.parameters import GenerationParameters


class Settings(BaseModel, extra='forbid', frozen=True):
    """Main settings of application.

    Attributes
    ----------
    server: ServerParameters
        Server parameters.

    generation: GenerationParameters
        Generation parameters.

    log : LogParameters
        Log parameters.

    path : PathParameters
        Path parameters.

    """

    server: ServerParameters
    generation: GenerationParameters
    log: LogParameters
    path: PathParameters
