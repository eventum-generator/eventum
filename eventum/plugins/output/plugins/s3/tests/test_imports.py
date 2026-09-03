import subprocess
import sys

MARKER = 'LOADED:'

PROBE = f"""
import sys
import eventum.plugins.output.plugins.s3.plugin  # noqa: F401
loaded = sorted(
    name
    for name in sys.modules
    if name == 'pyarrow' or name.startswith(('pyarrow.', 'obstore'))
)
print('{MARKER}' + ','.join(loaded))
"""


def _modules_loaded_by_the_plugin_module() -> list[str]:
    """Import the plugin module in a clean interpreter and report which
    of its heavy dependencies came along.
    """
    result = subprocess.run(  # noqa: S603
        [sys.executable, '-c', PROBE],
        capture_output=True,
        text=True,
        check=True,
    )
    reported = next(
        line.removeprefix(MARKER)
        for line in result.stdout.splitlines()
        if line.startswith(MARKER)
    )

    return [name for name in reported.split(',') if name]


def test_heavy_dependencies_are_not_loaded_by_the_plugin_module():
    """The plugin module is imported to build the config types of every
    generator, so its dependencies wait until the plugin is opened.
    """
    assert _modules_loaded_by_the_plugin_module() == []
