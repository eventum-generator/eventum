"""Models of startup file entries."""

from pydantic import Field, RootModel

from eventum.core.parameters import GeneratorParameters


class StartupGeneratorParameters(
    GeneratorParameters,
    extra='forbid',
    frozen=True,
):
    """Startup parameters for single generator.

    autostart : bool, default=True
        Whether to automatically start the generator.
    scenarios : list[str], default=[]
        Scenario names this generator belongs to.
    """

    autostart: bool = Field(default=True)
    scenarios: list[str] = Field(default_factory=list)


class StartupGeneratorParametersList(RootModel, frozen=True):
    """List of startup generator parameters."""

    root: tuple[StartupGeneratorParameters, ...] = Field()
