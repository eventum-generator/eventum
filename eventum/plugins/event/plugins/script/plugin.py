"""Definition of replay event plugin."""

from collections.abc import Callable
from importlib import util
from typing import override

from eventum.plugins.event.base.plugin import (
    EventPlugin,
    EventPluginParams,
    ProduceParams,
)
from eventum.plugins.event.exceptions import (
    PluginProduceError,
    PluginProduceSignal,
)
from eventum.plugins.event.plugins.script.config import ScriptEventPluginConfig
from eventum.plugins.exceptions import PluginConfigurationError


class ScriptEventPlugin(
    EventPlugin[ScriptEventPluginConfig, EventPluginParams],
):
    """Event plugin for producing events using script with user
    defined logic.

    Notes
    -----
    User script must include function with the following signature:
    ```
    def produce(params: ProduceParams) -> str | list[str]:
        ...
    ```
    For more information see documentation string of `ProduceParams`.

    """

    _FUNCTION_NAME = 'produce'

    @override
    def __init__(
        self,
        config: ScriptEventPluginConfig,
        params: EventPluginParams,
    ) -> None:
        super().__init__(config, params)

        self._logger.debug('Importing function from external module')
        self._function = self._import_function()

    def _import_function(self) -> Callable[[ProduceParams], str | list[str]]:
        """Import the function from the user defined module.

        Returns
        -------
        Callable[[ProduceParams], str | list[str]]
            Function.

        Raises
        ------
        PluginConfigurationError
            If module is not found, function is not found in module or
            other error occurred during module execution.

        """
        script_path = self.resolve_path(self._config.path)
        spec = util.spec_from_file_location('user_module', script_path)

        if spec is None:
            msg = 'Cannot get spec of script module'
            raise PluginConfigurationError(
                msg,
                context={'file_path': str(script_path)},
            )

        try:
            module = util.module_from_spec(spec)
        except Exception as e:
            msg = 'Failed to import script as external module'
            raise PluginConfigurationError(
                msg,
                context={
                    'reason': str(e),
                    'file_path': str(script_path),
                },
            ) from e

        if spec.loader is None:
            msg = 'Script cannot be executed due to loader problem'
            raise PluginConfigurationError(
                msg,
                context={'file_path': str(script_path)},
            )

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            msg = 'Exception occurred during script execution'
            raise PluginConfigurationError(
                msg,
                context={
                    'reason': str(e),
                    'file_path': str(script_path),
                },
            ) from e

        try:
            function = getattr(module, ScriptEventPlugin._FUNCTION_NAME)
        except AttributeError:
            msg = (
                f'Definition of function `{ScriptEventPlugin._FUNCTION_NAME}` '
                'is missing in script'
            )
            raise PluginConfigurationError(
                msg,
                context={'file_path': str(script_path)},
            ) from None

        return function

    @override
    def _produce(self, params: ProduceParams) -> list[str]:
        try:
            result = self._function(params)
        except PluginProduceSignal:
            raise
        except Exception as e:
            msg = 'Exception occurred during function execution'
            raise PluginProduceError(
                msg,
                context={
                    'reason': f'{e.__class__.__name__}: {e}',
                },
            ) from e

        if isinstance(result, str):
            return [result]
        if isinstance(result, list):
            types = {el.__class__.__name__ for el in result}
            if (not result) or ('str' in types and len(types) == 1):
                return result

            msg = (
                'Function returned object of invalid type, '
                'string or list of strings are expected'
            )
            raise PluginProduceError(
                msg,
                context={
                    'reason': (
                        f'Elements of next types encountered in list: {types}'
                    ),
                },
            )

        msg = (
            'Function returned object of invalid type, '
            'string or list of strings are expected'
        )
        raise PluginProduceError(
            msg,
            context={},
        )
