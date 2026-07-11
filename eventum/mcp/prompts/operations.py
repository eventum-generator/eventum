"""Live operations prompt for the Eventum MCP server (HTTP only)."""

from mcp.server.fastmcp import FastMCP

_LIVE_OPS = """\
Operate generators on a running Eventum server through the live (HTTP) \
tools. A safe loop:

1. SURVEY. `list_generators_live` lists every managed generator with \
its status; `get_generator_status` drills into one; \
`list_startup_generators` shows what is configured to start on boot.
2. REGISTER. For a generator already authored under the generators \
directory, `register_generator` adds it live and persists it to the \
startup file.
3. RUN. `start_generator` begins a run (idempotent if already running).
4. MONITOR. `get_generator_status` for the lifecycle flags, \
`get_generator_stats` for throughput and event counts; \
`get_generator_logs` for the recent log tail to diagnose a failure \
(absolute paths and secrets are scrubbed first).
5. RETIRE. `stop_generator` halts a run. To remove a generator for \
good, `unregister_generator` drops it from the runtime and the startup \
file; follow with `delete_generator` if you also want its files gone.

Modes. A generator runs in live mode (wall-clock synchronized \
streaming) or sample mode (max-speed bulk generation). The mode comes \
from the registered execution settings (`live_mode`); override it with \
the `execution` argument of `register_generator`. For a quick bounded \
sample without registering, use `run_generator`.

Scenarios and shared state. Group related generators into named \
scenarios: `list_scenarios` and `get_scenario` inspect them, while \
`add_generator_to_scenario`, `remove_generator_from_scenario`, and \
`delete_scenario` edit the tags in the startup file. Generators also \
coordinate at runtime through shared `globals` state: read it with \
`get_global_state` / `get_global_state_key`, edit it with \
`set_global_state`, `delete_global_state_key`, and `clear_global_state`.

Instance and settings. `eventum://instance/info` reports host and \
runtime metrics; `eventum://instance/settings` shows the running \
settings with credentials redacted and paths shortened. \
`update_settings` patches the settings file and applies on the next \
restart, so follow it with `restart_instance` to take effect; \
`stop_instance` halts the instance. Both lifecycle tools end this MCP \
connection, since the server runs inside the instance.

Write tools (register, start, stop, unregister, delete, file writes, \
scenario and global-state edits, settings updates, instance control) \
require the server to allow writes; when it does not, they fail and \
only the read tools work.
"""


def live_ops_text() -> str:
    """Return the live-operations guidance text."""
    return _LIVE_OPS


def register(mcp: FastMCP) -> None:
    """Register the live-operations prompt."""

    @mcp.prompt(
        name='live_ops',
        description=(
            'Operate generators on a running server: register, start, '
            'monitor, stop, and retire.'
        ),
    )
    def live_ops() -> str:
        return live_ops_text()
