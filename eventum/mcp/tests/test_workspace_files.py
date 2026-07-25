"""Tests for workspace file tools."""

from pathlib import Path

from eventum.mcp.context import FileAuthoringContext
from eventum.mcp.errors import ToolFailure
from eventum.mcp.tools.workspace_files import (
    _MAX_READ_BYTES,
    delete_generator,
    delete_generator_file,
    list_generator_files,
    list_generators,
    read_generator_file,
    write_generator_file,
)

# Small enough to page a test file in a handful of windows.
_LINE_LIMIT = 256


def _ctx(tmp_path: Path, *, read_only: bool = False) -> FileAuthoringContext:
    return FileAuthoringContext(generators_dir=tmp_path, read_only=read_only)


def _gen(tmp_path: Path, name: str = 'g') -> Path:
    d = tmp_path / name
    (d / 'templates').mkdir(parents=True)
    (d / 'generator.yml').write_text('input: []\nevent: {}\noutput: []\n')
    (d / 'templates' / 'a.jinja').write_text('hi')
    return d


def test_list_generators(tmp_path: Path) -> None:
    """Subdirs with generator.yml are listed; others are ignored."""
    _gen(tmp_path)
    (tmp_path / 'not-a-gen').mkdir()
    assert list_generators(_ctx(tmp_path)) == ['g']


def test_list_generators_empty_dir(tmp_path: Path) -> None:
    """Empty generators dir yields empty list."""
    assert list_generators(_ctx(tmp_path)) == []


def test_list_generators_missing_dir(tmp_path: Path) -> None:
    """Non-existent generators dir yields empty list."""
    ctx = FileAuthoringContext(
        generators_dir=tmp_path / 'nonexistent',
        read_only=False,
    )
    assert list_generators(ctx) == []


def test_list_generator_files(tmp_path: Path) -> None:
    """Allowed-extension files are returned with POSIX-relative paths."""
    _gen(tmp_path)
    files = list_generator_files(_ctx(tmp_path), 'g')
    assert not isinstance(files, ToolFailure)
    assert 'generator.yml' in files
    assert 'templates/a.jinja' in files


def test_list_generator_files_unknown(tmp_path: Path) -> None:
    """Unknown generator name returns ToolFailure."""
    result = list_generator_files(_ctx(tmp_path), 'missing')
    assert isinstance(result, ToolFailure)


def test_read_generator_file(tmp_path: Path) -> None:
    """A file within the window is returned whole and not truncated."""
    _gen(tmp_path)
    result = read_generator_file(_ctx(tmp_path), 'g', 'templates/a.jinja')
    assert result == {
        'content': 'hi',
        'offset': 0,
        'next_offset': None,
        'size_in_bytes': 2,
        'truncated': False,
    }


def test_read_generator_file_windows_large_file(tmp_path: Path) -> None:
    """A file over the limit is windowed and reports what is left.

    This is the regression guard: the whole file used to be returned, so
    an output file or a large sample landed in the agent's context in
    one piece.
    """
    d = _gen(tmp_path)
    lines = [f'{{"n": {i}}}\n' for i in range(400)]
    (d / 'big.json').write_text(''.join(lines))

    result = read_generator_file(
        _ctx(tmp_path), 'g', 'big.json', limit=_LINE_LIMIT
    )

    assert not isinstance(result, ToolFailure)
    assert result['truncated'] is True
    assert result['offset'] == 0
    assert result['size_in_bytes'] == len(''.join(lines))
    assert len(result['content'].encode()) <= _LINE_LIMIT
    # Windows end on a line break, so a page is never a partial line.
    assert result['content'].endswith('\n')
    assert result['next_offset'] == len(result['content'].encode())


def test_read_generator_file_pages_whole_file(tmp_path: Path) -> None:
    """Following next_offset reads the file without gaps or repeats."""
    d = _gen(tmp_path)
    content = ''.join(f'{{"n": {i}}}\n' for i in range(400))
    (d / 'big.json').write_text(content)

    pages: list[str] = []
    offset: int | None = 0

    while offset is not None:
        page = read_generator_file(
            _ctx(tmp_path), 'g', 'big.json', offset=offset, limit=_LINE_LIMIT
        )
        assert not isinstance(page, ToolFailure)
        pages.append(page['content'])
        offset = page['next_offset']

    assert ''.join(pages) == content


def test_read_generator_file_caps_limit(tmp_path: Path) -> None:
    """A limit above the cap is clamped instead of honoured."""
    d = _gen(tmp_path)
    content = 'x' * (_MAX_READ_BYTES * 2)
    (d / 'big.csv').write_text(content)

    result = read_generator_file(
        _ctx(tmp_path), 'g', 'big.csv', limit=_MAX_READ_BYTES * 2
    )

    assert not isinstance(result, ToolFailure)
    assert len(result['content']) == _MAX_READ_BYTES
    assert result['truncated'] is True


def test_read_generator_file_offset_past_end(tmp_path: Path) -> None:
    """An offset past the end of the file yields nothing to continue."""
    _gen(tmp_path)
    result = read_generator_file(
        _ctx(tmp_path), 'g', 'templates/a.jinja', offset=1000
    )

    assert result == {
        'content': '',
        'offset': 2,
        'next_offset': None,
        'size_in_bytes': 2,
        'truncated': False,
    }


def test_read_generator_file_not_found(tmp_path: Path) -> None:
    """Missing file returns ToolFailure."""
    _gen(tmp_path)
    result = read_generator_file(_ctx(tmp_path), 'g', 'missing.yml')
    assert isinstance(result, ToolFailure)


def test_read_generator_file_disallowed_extension(tmp_path: Path) -> None:
    """Files with disallowed extensions return ToolFailure."""
    d = _gen(tmp_path)
    (d / 'secret.py').write_text('pass')
    result = read_generator_file(_ctx(tmp_path), 'g', 'secret.py')
    assert isinstance(result, ToolFailure)


def test_read_traversal_rejected(tmp_path: Path) -> None:
    """Parent traversal in the read path returns ToolFailure."""
    _gen(tmp_path)
    result = read_generator_file(_ctx(tmp_path), 'g', '../../etc/passwd')
    assert isinstance(result, ToolFailure)


def test_read_absolute_rejected(tmp_path: Path) -> None:
    """Absolute read path returns ToolFailure."""
    _gen(tmp_path)
    result = read_generator_file(_ctx(tmp_path), 'g', '/etc/passwd')
    assert isinstance(result, ToolFailure)


def test_list_generator_files_traversal_name(tmp_path: Path) -> None:
    """Generator name that escapes the root returns ToolFailure."""
    _gen(tmp_path)
    result = list_generator_files(_ctx(tmp_path), '../escape')
    assert isinstance(result, ToolFailure)


def test_write_generator_file_roundtrip(tmp_path: Path) -> None:
    """Written content is readable back via read_generator_file."""
    _gen(tmp_path)
    res = write_generator_file(_ctx(tmp_path), 'g', 'templates/b.jinja', 'yo')
    assert res == {'written': 'templates/b.jinja'}

    read = read_generator_file(_ctx(tmp_path), 'g', 'templates/b.jinja')
    assert not isinstance(read, ToolFailure)
    assert read['content'] == 'yo'


def test_write_blocked_when_read_only(tmp_path: Path) -> None:
    """Write is blocked and file not created when context is read-only."""
    _gen(tmp_path)
    res = write_generator_file(
        _ctx(tmp_path, read_only=True), 'g', 'templates/c.jinja', 'x'
    )
    assert isinstance(res, ToolFailure)
    assert not (tmp_path / 'g' / 'templates' / 'c.jinja').exists()


def test_write_traversal_rejected(tmp_path: Path) -> None:
    """Path traversal attempt returns ToolFailure."""
    _gen(tmp_path)
    res = write_generator_file(_ctx(tmp_path), 'g', '../../evil.txt', 'x')
    assert isinstance(res, ToolFailure)


def test_write_disallowed_extension(tmp_path: Path) -> None:
    """Disallowed extension returns ToolFailure and writes nothing."""
    _gen(tmp_path)
    res = write_generator_file(_ctx(tmp_path), 'g', 'script.py', 'code')
    assert isinstance(res, ToolFailure)
    assert not (tmp_path / 'g' / 'script.py').exists()


def test_list_generators_sorted(tmp_path: Path) -> None:
    """Generator names are returned in sorted order."""
    for name in ['zebra', 'alpha', 'middle']:
        _gen(tmp_path, name)
    assert list_generators(_ctx(tmp_path)) == ['alpha', 'middle', 'zebra']


def test_delete_generator_file_removes_file(tmp_path: Path) -> None:
    """A file is deleted and no longer present."""
    _gen(tmp_path)
    res = delete_generator_file(_ctx(tmp_path), 'g', 'templates/a.jinja')
    assert res == {'deleted': 'templates/a.jinja'}
    assert not (tmp_path / 'g' / 'templates' / 'a.jinja').exists()


def test_delete_generator_file_blocked_when_read_only(
    tmp_path: Path,
) -> None:
    """Read-only blocks deletion and leaves the file in place."""
    _gen(tmp_path)
    res = delete_generator_file(
        _ctx(tmp_path, read_only=True), 'g', 'templates/a.jinja'
    )
    assert isinstance(res, ToolFailure)
    assert (tmp_path / 'g' / 'templates' / 'a.jinja').exists()


def test_delete_generator_file_not_found(tmp_path: Path) -> None:
    """Missing file returns ToolFailure."""
    _gen(tmp_path)
    res = delete_generator_file(_ctx(tmp_path), 'g', 'templates/x.jinja')
    assert isinstance(res, ToolFailure)


def test_delete_generator_file_disallowed_extension(
    tmp_path: Path,
) -> None:
    """Disallowed extension returns ToolFailure and keeps the file."""
    d = _gen(tmp_path)
    (d / 'secret.py').write_text('pass')
    res = delete_generator_file(_ctx(tmp_path), 'g', 'secret.py')
    assert isinstance(res, ToolFailure)
    assert (d / 'secret.py').exists()


def test_delete_generator_file_traversal_rejected(tmp_path: Path) -> None:
    """Parent traversal in the delete path returns ToolFailure."""
    _gen(tmp_path)
    res = delete_generator_file(_ctx(tmp_path), 'g', '../../etc/passwd')
    assert isinstance(res, ToolFailure)


def test_delete_generator_removes_dir(tmp_path: Path) -> None:
    """The whole generator directory is removed."""
    _gen(tmp_path)
    res = delete_generator(_ctx(tmp_path), 'g')
    assert res == {'deleted': 'g'}
    assert not (tmp_path / 'g').exists()


def test_delete_generator_blocked_when_read_only(tmp_path: Path) -> None:
    """Read-only blocks directory deletion."""
    _gen(tmp_path)
    res = delete_generator(_ctx(tmp_path, read_only=True), 'g')
    assert isinstance(res, ToolFailure)
    assert (tmp_path / 'g').exists()


def test_delete_generator_missing(tmp_path: Path) -> None:
    """Unknown generator name returns ToolFailure."""
    res = delete_generator(_ctx(tmp_path), 'missing')
    assert isinstance(res, ToolFailure)


def test_delete_generator_root_rejected(tmp_path: Path) -> None:
    """Deleting the generators dir itself is rejected; it survives."""
    _gen(tmp_path)
    res = delete_generator(_ctx(tmp_path), '.')
    assert isinstance(res, ToolFailure)
    assert tmp_path.exists()


def test_delete_generator_traversal_rejected(tmp_path: Path) -> None:
    """A name escaping the generators root returns ToolFailure."""
    _gen(tmp_path)
    res = delete_generator(_ctx(tmp_path), '../escape')
    assert isinstance(res, ToolFailure)


def test_delete_generator_nested_dir_rejected(tmp_path: Path) -> None:
    """A nested (non-top-level) directory cannot be deleted."""
    _gen(tmp_path)
    res = delete_generator(_ctx(tmp_path), 'g/templates')
    assert isinstance(res, ToolFailure)
    assert (tmp_path / 'g' / 'templates').exists()
