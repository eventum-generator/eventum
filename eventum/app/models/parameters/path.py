"""Path parameters."""

from pathlib import Path

from pydantic import BaseModel, field_validator

DEFAULT_REPOSITORIES_FILENAME = 'repositories.yml'


class PathParameters(BaseModel, extra='forbid', frozen=True):
    """Path parameters.

    Attributes
    ----------
    logs : Path
        Absolute path to logs directory.

    startup : Path
        Absolute path to file with list of generators to run at startup.

    generators_dir : Path
        Absolute path to directory with generators configuration files.

    keyring_cryptfile : Path
        Absolute path to keyring encrypted file with stored secrets

    repositories : Path | None, default=None
        Absolute path to file with list of connected generator
        repositories. When not provided, the file named
        "repositories.yml" next to the startup file is used.

    generator_config_filename : Path, default='generator.yml'
        Filename for generator configurations. This parameter is used
        by the API for detection directories with generator
        configurations. Directory with generator configuration named
        other than this parameter value will not be operable using API
        endpoints.

    """

    logs: Path
    startup: Path
    generators_dir: Path
    keyring_cryptfile: Path
    repositories: Path | None = None
    generator_config_filename: Path = Path('generator.yml')

    @property
    def repositories_file(self) -> Path:
        """Location the list of connected repositories is kept in."""
        if self.repositories is not None:
            return self.repositories

        return self.startup.parent / DEFAULT_REPOSITORIES_FILENAME

    @field_validator('logs', 'startup', 'generators_dir', 'keyring_cryptfile')
    @classmethod
    def validate_absolute_paths(cls, v: Path) -> Path:  # noqa: D102
        if not v.is_absolute():
            msg = 'Path must be absolute'
            raise ValueError(msg)

        return v

    @field_validator('repositories')
    @classmethod
    def validate_optional_absolute_path(cls, v: Path | None) -> Path | None:  # noqa: D102
        if v is not None and not v.is_absolute():
            msg = 'Path must be absolute'
            raise ValueError(msg)

        return v

    @field_validator('generator_config_filename')
    @classmethod
    def validate_generator_config_filename(cls, v: Path) -> Path:  # noqa: D102
        if v.is_absolute() or len(v.parts) != 1:
            msg = 'Only filename must be provided'
            raise ValueError(msg)

        if v.suffix not in ('.yml', '.yaml'):
            msg = 'File extension must be "yml" or "yaml"'
            raise ValueError(msg)

        return v
