import threading
import time
from types import SimpleNamespace

from pydantic import RootModel

import eventum.plugins.input.plugins as input_plugins
from eventum.plugins import loader
from eventum.plugins.event.base.config import EventPluginConfig
from eventum.plugins.event.base.plugin import EventPlugin
from eventum.plugins.input.base.config import InputPluginConfig
from eventum.plugins.input.base.plugin import InputPlugin
from eventum.plugins.loader import (
    _invoke_plugin,
    get_event_plugin_names,
    get_input_plugin_names,
    get_output_plugin_names,
    load_event_plugin,
    load_input_plugin,
    load_output_plugin,
)
from eventum.plugins.output.base.config import OutputPluginConfig
from eventum.plugins.output.base.plugin import OutputPlugin


def test_loading_input_plugin():
    plugin_names = get_input_plugin_names()

    assert plugin_names

    for plugin_name in plugin_names:
        plugin_info = load_input_plugin(plugin_name)

        assert plugin_info.name == plugin_name
        assert plugin_info.type == 'input'
        assert issubclass(plugin_info.cls, InputPlugin)
        assert issubclass(
            plugin_info.config_cls, InputPluginConfig
        ) or issubclass(plugin_info.config_cls, RootModel)


def test_loading_event_plugins():
    plugin_names = get_event_plugin_names()

    assert plugin_names

    for plugin_name in plugin_names:
        plugin_info = load_event_plugin(plugin_name)

        assert plugin_info.name == plugin_name
        assert plugin_info.type == 'event'
        assert issubclass(plugin_info.cls, EventPlugin)
        assert issubclass(
            plugin_info.config_cls, EventPluginConfig
        ) or issubclass(plugin_info.config_cls, RootModel)


def test_loading_output_plugins():
    plugin_names = get_output_plugin_names()

    assert plugin_names

    for plugin_name in plugin_names:
        plugin_info = load_output_plugin(plugin_name)

        assert plugin_info.name == plugin_name
        assert plugin_info.type == 'output'
        assert issubclass(plugin_info.cls, OutputPlugin)
        assert issubclass(
            plugin_info.config_cls, OutputPluginConfig
        ) or issubclass(plugin_info.config_cls, RootModel)


def test_concurrent_invocation_imports_modules_one_at_a_time(monkeypatch):
    """Threads invoking different plugins never import at the same time."""
    importing = 0
    max_importing = 0
    counters_lock = threading.Lock()

    def fake_import(_module_name: str) -> None:
        nonlocal importing, max_importing

        with counters_lock:
            importing += 1
            max_importing = max(max_importing, importing)

        time.sleep(0.01)

        with counters_lock:
            importing -= 1

    monkeypatch.setattr(
        loader,
        'importlib',
        SimpleNamespace(import_module=fake_import),
    )

    threads = [
        threading.Thread(
            target=_invoke_plugin,
            args=(input_plugins, f'plugin_{i}'),
        )
        for i in range(8)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert max_importing == 1


def test_invocation_from_plugin_module_does_not_deadlock(monkeypatch):
    """Plugin loaded while another one is imported in the same thread."""
    imported_modules: list[str] = []

    def fake_import(module_name: str) -> None:
        imported_modules.append(module_name)

        if len(imported_modules) == 1:
            _invoke_plugin(input_plugins, 'nested')

    monkeypatch.setattr(
        loader,
        'importlib',
        SimpleNamespace(import_module=fake_import),
    )

    # Invoked in a separate daemon thread so that a lost reentrancy
    # fails the test instead of hanging the whole run.
    thread = threading.Thread(
        target=_invoke_plugin,
        args=(input_plugins, 'outer'),
        daemon=True,
    )
    thread.start()
    thread.join(timeout=5)

    assert not thread.is_alive()
    assert imported_modules == [
        'eventum.plugins.input.plugins.outer.plugin',
        'eventum.plugins.input.plugins.nested.plugin',
    ]


def test_concurrent_loading_of_all_plugins():
    """Every plugin loads when several threads load them at once."""
    loadings = [
        *[(load_input_plugin, name) for name in get_input_plugin_names()],
        *[(load_event_plugin, name) for name in get_event_plugin_names()],
        *[(load_output_plugin, name) for name in get_output_plugin_names()],
    ]
    threads_count = 4
    barrier = threading.Barrier(threads_count)
    loaded_names: list[str] = []
    errors: list[Exception] = []

    def load_all() -> None:
        barrier.wait()
        try:
            for load, name in loadings:
                loaded_names.append(load(name).name)
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=load_all) for _ in range(threads_count)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert not errors
    assert len(loaded_names) == threads_count * len(loadings)
