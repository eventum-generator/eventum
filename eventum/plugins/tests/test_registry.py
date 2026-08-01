import importlib
import threading

import pytest

from eventum.plugins.registry import PluginInfo, PluginsRegistry


@pytest.fixture(autouse=True)
def clean_registry():
    PluginsRegistry.clear()
    yield
    PluginsRegistry.clear()


def test_registry():
    assert not PluginsRegistry.is_registered('input', 'test')

    with pytest.raises(ValueError):
        PluginsRegistry.get_plugin_info('input', 'test')

    PluginsRegistry.register_plugin(
        PluginInfo(name='test', cls=object, config_cls=object, type='input')
    )

    assert PluginsRegistry.is_registered('input', 'test')

    plugin_info = PluginsRegistry.get_plugin_info('input', 'test')

    assert plugin_info.name == 'test'
    assert plugin_info.type == 'input'
    assert plugin_info.cls is object
    assert plugin_info.config_cls is object


def test_registry_clearing():
    PluginsRegistry.register_plugin(
        PluginInfo(name='test', cls=object, config_cls=object, type='input')
    )

    assert PluginsRegistry.is_registered('input', 'test')

    PluginsRegistry.clear()

    assert not PluginsRegistry.is_registered('input', 'test')


class InterleavingRegistry(dict):
    """Registry storage that suspends the thread reading it first.

    Reading the registry before writing to it is exactly what makes a
    registration lose a concurrent one, so the reader is held until
    another registration of the same type completes. A registration
    that reads and writes in a single step never reads the storage,
    leaving nothing to interleave.
    """

    def __init__(self) -> None:
        super().__init__()
        self.read = threading.Event()
        self.other_registered = threading.Event()

    def __contains__(self, key: object) -> bool:
        result = super().__contains__(key)

        if not self.read.is_set():
            self.read.set()
            self.other_registered.wait(timeout=5)

        return result


def test_registration_does_not_drop_concurrent_one(monkeypatch):
    """Plugin registered while another registration is in progress."""
    registry = InterleavingRegistry()
    monkeypatch.setattr(PluginsRegistry, '_registry', registry)

    def register_suspended() -> None:
        PluginsRegistry.register_plugin(
            PluginInfo(
                name='suspended',
                cls=object,
                config_cls=object,
                type='input',
            )
        )

    thread = threading.Thread(target=register_suspended, daemon=True)
    thread.start()

    # Expires without suspending anyone when registration is atomic.
    registry.read.wait(timeout=1)

    PluginsRegistry.register_plugin(
        PluginInfo(
            name='completed',
            cls=object,
            config_cls=object,
            type='input',
        )
    )
    registry.other_registered.set()
    thread.join(timeout=5)

    assert not thread.is_alive()
    assert set(registry['input']) == {'completed', 'suspended'}


def test_plugin_registration():
    PluginsRegistry.clear()

    assert not PluginsRegistry.is_registered('input', 'cron')

    from eventum.plugins.input.plugins.cron import config, plugin

    importlib.reload(plugin)

    assert PluginsRegistry.is_registered('input', 'cron')

    plugin_info = PluginsRegistry.get_plugin_info('input', 'cron')

    assert plugin_info.name == 'cron'
    assert plugin_info.type == 'input'
    assert plugin_info.cls is plugin.CronInputPlugin
    assert plugin_info.config_cls is config.CronInputPluginConfig
