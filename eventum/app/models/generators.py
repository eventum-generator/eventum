"""Model for the list of generators."""

from collections.abc import Sequence

from flatten_dict import flatten, unflatten  # type: ignore[import-untyped]
from pydantic import Field, RootModel

from eventum.core.parameters import GenerationParameters, GeneratorParameters


class StartupGeneratorParameters(
    GeneratorParameters,
    extra='forbid',
    frozen=True,
):
    """Startup parameters for single generator.

    autostart : bool, default=True
        Whether to automatically start the generator.
    """

    autostart: bool = Field(default=True)


class StartupGeneratorParametersList(RootModel, frozen=True):
    """List of startup generator parameters."""

    root: tuple[StartupGeneratorParameters, ...] = Field()

    @classmethod
    def build_over_generation_parameters(
        cls,
        object: Sequence[dict],
        generation_parameters: GenerationParameters,
    ) -> 'StartupGeneratorParametersList':
        """Build instance using sequence of startup generator parameters
        that are going to be combined with base generation parameters
        from `GenerationParameters` object.

        Parameters
        ----------
        object : Sequence[dict]
            Sequence of generator startup parameters.

        generation_parameters : GenerationParameters
            Base generation parameters.

        Returns
        -------
        StartupGeneratorParametersList
            Generator startup parameters list.

        Raises
        ------
        ValidationError
            If object cannot be validated.

        """
        generators: list[StartupGeneratorParameters] = []
        base_params = generation_parameters.model_dump()
        base_params = flatten(base_params, reducer='dot')

        for params in object:
            generator_params = flatten(params, reducer='dot')

            generator_params = base_params | generator_params
            generator_params = unflatten(generator_params, splitter='dot')

            validated_generator_params = (
                StartupGeneratorParameters.model_validate(
                    generator_params,
                )
            )

            generators.append(validated_generator_params)

        return StartupGeneratorParametersList(root=tuple(generators))
