"""Models."""

from pydantic import BaseModel, Field


class RenameSecretRequest(BaseModel, frozen=True):
    """New name for an existing secret."""

    new_name: str = Field(min_length=1, description='New secret name')


class SecretReferencesResponse(BaseModel, frozen=True):
    """Everything that refers to a secret, grouped by kind.

    Attributes
    ----------
    projects : list[str]
        Names of the projects whose configuration reads the secret.

    repositories : list[str]
        Names of the repositories authenticating with the secret.

    """

    projects: list[str] = Field(
        description=(
            'Names of the projects whose configuration reads the '
            'secret as `${secrets.<name>}`'
        ),
    )
    repositories: list[str] = Field(
        description=(
            'Names of the connected repositories authenticating with '
            'the secret'
        ),
    )


class RenamedReferencesResponse(BaseModel, frozen=True):
    """Referrers a rename carried over to the new name, by kind.

    Attributes
    ----------
    projects : list[str]
        Names of the projects whose configuration was rewritten.

    repositories : list[str]
        Names of the repositories that were repointed.

    """

    projects: list[str] = Field(
        description=(
            'Names of the projects whose configuration was rewritten '
            'for the new name'
        ),
    )
    repositories: list[str] = Field(
        description=(
            'Names of the connected repositories that were repointed '
            'at the new name'
        ),
    )
