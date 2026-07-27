"""Models."""

from pydantic import BaseModel, Field


class RenameSecretRequest(BaseModel, frozen=True):
    """New name for an existing secret."""

    new_name: str = Field(min_length=1, description='New secret name')
