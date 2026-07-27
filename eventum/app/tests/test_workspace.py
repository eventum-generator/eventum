"""Tests for transport-neutral generator-workspace helper."""

import os
from pathlib import Path

import pytest

from eventum.app.workspace import (
    WorkspaceError,
    delete_dir,
    delete_file,
    ensure_relative,
    find_secret_references,
    read_text,
    read_text_window,
    rename_generator_dir,
    resolve_generator_dir,
    resolve_generator_file,
    write_text,
)

_symlink_supported = hasattr(os, 'symlink')


def test_resolve_generator_dir_ok(tmp_path: Path):
    assert (
        resolve_generator_dir(tmp_path, 'gen') == (tmp_path / 'gen').resolve()
    )


def test_resolve_generator_dir_escapes_rejected(tmp_path: Path):
    with pytest.raises(WorkspaceError):
        resolve_generator_dir(tmp_path, '../escape')


def test_resolve_generator_file_traversal_rejected(tmp_path: Path):
    with pytest.raises(WorkspaceError):
        resolve_generator_file(tmp_path, 'gen', Path('../../etc/passwd'))


def test_resolve_generator_file_absolute_rejected(tmp_path: Path):
    with pytest.raises(WorkspaceError):
        resolve_generator_file(tmp_path, 'gen', Path('/etc/passwd'))


def test_ensure_relative_returns_path():
    p = Path('a/b/c.yml')
    assert ensure_relative(p) is p


def test_read_write_text_roundtrip(tmp_path: Path):
    target = tmp_path / 'sub' / 'file.txt'
    target.parent.mkdir()
    write_text(target, 'hello')
    assert read_text(target) == 'hello'


def test_write_text_creates_parent_dirs(tmp_path: Path):
    target = tmp_path / 'deep' / 'nested' / 'file.txt'
    write_text(target, 'data')
    assert target.read_text() == 'data'


def test_resolve_generator_file_ok(tmp_path: Path):
    result = resolve_generator_file(tmp_path, 'gen', Path('sub/conf.yml'))
    assert result == (tmp_path / 'gen' / 'sub' / 'conf.yml').resolve()


@pytest.mark.skipif(
    not _symlink_supported,
    reason='platform does not support symlinks',
)
def test_resolve_generator_dir_symlinked_base_ok(tmp_path: Path):
    real = tmp_path / 'real'
    real.mkdir()
    link = tmp_path / 'link'
    link.symlink_to(real, target_is_directory=True)

    result = resolve_generator_dir(link, 'gen')

    assert result == (real / 'gen').resolve()
    assert result.is_relative_to(real.resolve())


@pytest.mark.skipif(
    not _symlink_supported,
    reason='platform does not support symlinks',
)
def test_resolve_generator_file_symlink_leaf_escape_rejected(tmp_path: Path):
    gens = tmp_path / 'generators'
    gen = gens / 'gen'
    gen.mkdir(parents=True)
    outside = tmp_path / 'outside'
    outside.mkdir()
    secret = outside / 'secret.yml'
    secret.write_text('TOP SECRET')
    (gen / 'link.yml').symlink_to(secret)

    with pytest.raises(WorkspaceError):
        resolve_generator_file(gens, 'gen', Path('link.yml'))


@pytest.mark.skipif(
    not _symlink_supported,
    reason='platform does not support symlinks',
)
def test_resolve_generator_file_symlink_component_escape_rejected(
    tmp_path: Path,
):
    gens = tmp_path / 'generators'
    gen = gens / 'gen'
    gen.mkdir(parents=True)
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'secret.yml').write_text('TOP SECRET')
    (gen / 'sub').symlink_to(outside, target_is_directory=True)

    with pytest.raises(WorkspaceError):
        resolve_generator_file(gens, 'gen', Path('sub/secret.yml'))


def test_read_text_missing_path_raises(tmp_path: Path):
    missing = tmp_path / 'nope.txt'
    with pytest.raises(WorkspaceError) as exc_info:
        read_text(missing)
    assert exc_info.value.context['file_path'] == str(missing)


def test_read_text_non_utf8_raises(tmp_path: Path) -> None:
    """A non-UTF-8 file raises WorkspaceError, not a decode error."""
    target = tmp_path / 'sample.csv'
    target.write_bytes('caf\xe9;1\n'.encode('latin-1'))
    with pytest.raises(WorkspaceError) as exc_info:
        read_text(target)
    assert exc_info.value.context['file_path'] == str(target)


def test_write_text_unencodable_raises(tmp_path: Path) -> None:
    """Unencodable content raises WorkspaceError, not an encode error."""
    target = tmp_path / 'file.txt'
    with pytest.raises(WorkspaceError) as exc_info:
        write_text(target, 'lone surrogate: \ud800')
    assert exc_info.value.context['file_path'] == str(target)


def test_write_text_parent_is_file_raises(tmp_path: Path):
    blocker = tmp_path / 'blocker'
    blocker.write_text('x')
    target = blocker / 'child.txt'
    with pytest.raises(WorkspaceError) as exc_info:
        write_text(target, 'data')
    assert exc_info.value.context['file_path'] == str(target)


def test_delete_file_removes_file(tmp_path: Path):
    target = tmp_path / 'file.txt'
    target.write_text('x')
    delete_file(target)
    assert not target.exists()


def test_delete_file_missing_raises(tmp_path: Path):
    missing = tmp_path / 'nope.txt'
    with pytest.raises(WorkspaceError) as exc_info:
        delete_file(missing)
    assert exc_info.value.context['file_path'] == str(missing)


def test_delete_dir_removes_tree(tmp_path: Path):
    root = tmp_path / 'gen'
    (root / 'sub').mkdir(parents=True)
    (root / 'sub' / 'f.txt').write_text('x')
    delete_dir(root)
    assert not root.exists()


def test_delete_dir_missing_raises(tmp_path: Path):
    missing = tmp_path / 'nope'
    with pytest.raises(WorkspaceError) as exc_info:
        delete_dir(missing)
    assert exc_info.value.context['file_path'] == str(missing)


def test_rename_generator_dir_moves_directory(tmp_path: Path):
    source = tmp_path / 'gen'
    (source / 'templates').mkdir(parents=True)
    (source / 'generator.yml').write_text('input: []\n')

    result = rename_generator_dir(tmp_path, 'gen', 'renamed')

    assert result == (tmp_path / 'renamed').resolve()
    assert not source.exists()
    assert (tmp_path / 'renamed' / 'templates').is_dir()
    assert (
        tmp_path / 'renamed' / 'generator.yml'
    ).read_text() == 'input: []\n'


def test_rename_generator_dir_missing_source_raises(tmp_path: Path):
    with pytest.raises(WorkspaceError) as exc_info:
        rename_generator_dir(tmp_path, 'absent', 'renamed')
    assert exc_info.value.context['name'] == 'absent'


def test_rename_generator_dir_existing_target_raises(tmp_path: Path):
    (tmp_path / 'gen').mkdir()
    (tmp_path / 'taken').mkdir()

    with pytest.raises(WorkspaceError) as exc_info:
        rename_generator_dir(tmp_path, 'gen', 'taken')

    assert exc_info.value.context['name'] == 'taken'
    assert (tmp_path / 'gen').is_dir()


def test_rename_generator_dir_nested_target_rejected(tmp_path: Path):
    (tmp_path / 'gen').mkdir()

    with pytest.raises(WorkspaceError) as exc_info:
        rename_generator_dir(tmp_path, 'gen', 'nested/renamed')

    assert exc_info.value.context['name'] == 'nested/renamed'
    assert (tmp_path / 'gen').is_dir()


def test_rename_generator_dir_escaping_target_rejected(tmp_path: Path):
    (tmp_path / 'gen').mkdir()

    with pytest.raises(WorkspaceError):
        rename_generator_dir(tmp_path, 'gen', '../escape')

    assert (tmp_path / 'gen').is_dir()


def test_rename_generator_dir_escaping_source_rejected(tmp_path: Path):
    with pytest.raises(WorkspaceError):
        rename_generator_dir(tmp_path, '../escape', 'renamed')


_CONFIG_FILENAME = Path('generator.yml')


def _write_config(generators_dir: Path, name: str, content: str) -> None:
    """Create a generator directory holding the given config content."""
    config_path = generators_dir / name / _CONFIG_FILENAME
    config_path.parent.mkdir(parents=True)
    config_path.write_text(content)


def test_find_secret_references_matches_referencing_dirs(tmp_path: Path):
    _write_config(tmp_path, 'gen-a', 'token: ${secrets.api_key}\n')
    _write_config(tmp_path, 'gen-b', 'token: ${ secrets.api_key }\n')
    _write_config(tmp_path, 'gen-c', 'token: ${secrets.other}\n')
    _write_config(tmp_path, 'gen-d', 'host: ${params.host}\n')

    assert find_secret_references(tmp_path, _CONFIG_FILENAME, 'api_key') == [
        'gen-a',
        'gen-b',
    ]


def test_find_secret_references_ignores_dirs_without_config(tmp_path: Path):
    (tmp_path / 'not-a-generator').mkdir()
    (tmp_path / 'not-a-generator' / 'other.yml').write_text(
        'token: ${secrets.api_key}\n'
    )

    assert find_secret_references(tmp_path, _CONFIG_FILENAME, 'api_key') == []


def test_find_secret_references_skips_unreadable_config(tmp_path: Path):
    _write_config(tmp_path, 'gen-a', 'token: ${secrets.api_key}\n')
    (tmp_path / 'gen-b' / _CONFIG_FILENAME).parent.mkdir(parents=True)
    (tmp_path / 'gen-b' / _CONFIG_FILENAME).write_bytes(b'\xff\xfe\x00')

    assert find_secret_references(tmp_path, _CONFIG_FILENAME, 'api_key') == [
        'gen-a'
    ]


def test_find_secret_references_missing_dir_returns_empty(tmp_path: Path):
    assert (
        find_secret_references(
            tmp_path / 'absent', _CONFIG_FILENAME, 'api_key'
        )
        == []
    )


def test_window_holds_whole_small_file(tmp_path: Path) -> None:
    """A file inside the limit comes back with nothing to continue."""
    target = tmp_path / 'sample.csv'
    target.write_text('host,role\nweb-01,frontend\n')

    window = read_text_window(target, offset=0, limit=1024)

    assert window.content == 'host,role\nweb-01,frontend\n'
    assert window.offset == 0
    assert window.next_offset is None
    assert window.size_in_bytes == target.stat().st_size


def test_window_ends_on_a_complete_line(tmp_path: Path) -> None:
    """A window cut mid-line is trimmed back to the last line break."""
    target = tmp_path / 'events.json'
    target.write_text('aaaa\nbbbb\ncccc\n')

    window = read_text_window(target, offset=0, limit=12)

    assert window.content == 'aaaa\nbbbb\n'
    assert window.next_offset == 10


def test_windows_page_the_whole_file(tmp_path: Path) -> None:
    """Following next_offset reads every byte exactly once."""
    target = tmp_path / 'events.json'
    content = ''.join(f'line {i}\n' for i in range(500))
    target.write_text(content)

    pages: list[str] = []
    offset: int | None = 0

    while offset is not None:
        window = read_text_window(target, offset=offset, limit=64)
        pages.append(window.content)
        offset = window.next_offset

    assert ''.join(pages) == content


def test_window_keeps_an_oversized_line(tmp_path: Path) -> None:
    """A window without a line break is returned as it is.

    A minified JSON file is one long line; trimming it to a line break
    would yield nothing and the read would never advance.
    """
    target = tmp_path / 'events.json'
    target.write_text('x' * 100)

    window = read_text_window(target, offset=0, limit=10)

    assert window.content == 'x' * 10
    assert window.next_offset == 10


def test_window_past_the_end_is_empty(tmp_path: Path) -> None:
    """An offset beyond the file yields an empty final window."""
    target = tmp_path / 'sample.csv'
    target.write_text('host\n')

    window = read_text_window(target, offset=999, limit=64)

    assert window.content == ''
    assert window.offset == window.size_in_bytes
    assert window.next_offset is None


def test_window_advances_on_a_non_positive_limit(tmp_path: Path) -> None:
    """A limit below one still reads a byte instead of standing still."""
    target = tmp_path / 'sample.csv'
    target.write_text('abc')

    window = read_text_window(target, offset=0, limit=0)

    assert window.content == 'a'
    assert window.next_offset == 1


def test_window_replaces_undecodable_bytes(tmp_path: Path) -> None:
    """A window starting inside a character does not fail the read."""
    target = tmp_path / 'sample.csv'
    target.write_bytes(b'h\xc3\xa9llo')

    window = read_text_window(target, offset=2, limit=64)

    assert window.content == '�llo'
    assert window.next_offset is None


def test_window_of_missing_file_raises(tmp_path: Path) -> None:
    """A missing file is reported as a workspace error."""
    missing = tmp_path / 'absent.csv'
    with pytest.raises(WorkspaceError) as exc_info:
        read_text_window(missing, offset=0, limit=64)
    assert exc_info.value.context['file_path'] == str(missing)
