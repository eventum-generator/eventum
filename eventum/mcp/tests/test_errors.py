from pathlib import Path

from eventum.core.config_loader import ConfigurationLoadError
from eventum.mcp.errors import ToolFailure, to_tool_error


def test_scrub_relativizes_paths_and_allowlists(tmp_path: Path):
    gens = tmp_path / 'generators'
    secret = 'sup3r-secret-value'
    err = ConfigurationLoadError(
        'Invalid configuration',
        context={
            'file_path': str(gens / 'g' / 'generator.yml'),
            'reason': f'field "password": {secret!r} - invalid',
        },
    )
    failure = to_tool_error(err, generators_dir=gens)

    assert isinstance(failure, ToolFailure)
    assert failure.error == 'Invalid configuration'
    assert str(gens) not in repr(failure.details)
    assert failure.details.get('file_path') == 'g/generator.yml'
    assert secret in failure.details['reason']


def test_scrub_drops_unknown_keys(tmp_path: Path):
    err = ConfigurationLoadError(
        'x',
        context={'file_path': str(tmp_path / 'a'), 'internal_ptr': '0xdead'},
    )
    failure = to_tool_error(err, generators_dir=tmp_path)
    assert 'internal_ptr' not in failure.details


def test_scrub_falls_back_to_basename_outside_generators_dir(
    tmp_path: Path,
):
    err = ConfigurationLoadError(
        'x',
        context={'file_path': '/etc/passwd'},
    )
    failure = to_tool_error(err, generators_dir=tmp_path)
    assert failure.details['file_path'] == 'passwd'
    assert '/etc' not in repr(failure.details)
