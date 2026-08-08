"""Model for the main settings of the application."""

from pathlib import Path

import yaml
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


def write_settings(settings: Settings, path: Path) -> None:
    """Serialize settings to YAML and write them to a file.

    The single place that knows the on-disk settings format, shared by
    every transport that persists settings. Performs blocking file IO;
    call it from a worker thread on the event loop.

    Parameters
    ----------
    settings : Settings
        Settings to persist.

    path : Path
        Destination settings file.

    Raises
    ------
    OSError
        If the file cannot be written.

    """
    content = yaml.dump(
        settings.model_dump(mode='json', exclude_unset=True),
        sort_keys=False,
        allow_unicode=True,
    )
    path.write_text(content, encoding='utf-8')
