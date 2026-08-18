"""Tests for project archive tools."""

import base64
import io
import zipfile
from pathlib import Path

from eventum.mcp.context import FileAuthoringContext
from eventum.mcp.errors import ToolFailure
from eventum.mcp.tools import archives
from eventum.mcp.tools.archives import export_generator, import_generator


def _ctx(tmp_path: Path, *, read_only: bool = False) -> FileAuthoringContext:
    return FileAuthoringContext(generators_dir=tmp_path, read_only=read_only)


def _gen(tmp_path: Path, name: str = 'g') -> Path:
    d = tmp_path / name
    (d / 'templates').mkdir(parents=True)
    (d / 'generator.yml').write_text('input: []\n')
    (d / 'templates' / 'a.jinja').write_text('hi')
    return d


def _archive_names(content_base64: str) -> set[str]:
    content = base64.b64decode(content_base64)

    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        return {name.rstrip('/') for name in archive.namelist()}


def _encoded_archive(entries: dict[str, str]) -> str:
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, mode='w') as archive:
        for name, content in entries.items():
            archive.writestr(name, content)

    return base64.b64encode(buffer.getvalue()).decode('ascii')


def test_export_returns_archive(tmp_path: Path) -> None:
    """Whole generator directory is returned base64 encoded."""
    _gen(tmp_path)

    result = export_generator(_ctx(tmp_path), 'g')

    assert not isinstance(result, ToolFailure)
    assert result['filename'] == 'g.zip'
    assert result['size_in_bytes'] > 0
    assert _archive_names(result['content_base64']) == {
        'generator.yml',
        'templates',
        'templates/a.jinja',
    }


def test_export_excludes_entries(tmp_path: Path) -> None:
    """Named top level entries are left out."""
    generator = _gen(tmp_path)
    (generator / 'output').mkdir()
    (generator / 'output' / 'events.log').write_text('event')

    result = export_generator(_ctx(tmp_path), 'g', ['output'])

    assert not isinstance(result, ToolFailure)
    assert _archive_names(result['content_base64']) == {
        'generator.yml',
        'templates',
        'templates/a.jinja',
    }


def test_export_rejects_excluded_configuration(tmp_path: Path) -> None:
    """Configuration cannot be excluded - the archive needs it."""
    _gen(tmp_path)

    result = export_generator(_ctx(tmp_path), 'g', ['generator.yml'])

    assert isinstance(result, ToolFailure)


def test_export_rejects_nested_exclude(tmp_path: Path) -> None:
    """Only top level entry names are accepted."""
    _gen(tmp_path)

    result = export_generator(_ctx(tmp_path), 'g', ['templates/a.jinja'])

    assert isinstance(result, ToolFailure)


def test_export_missing_generator(tmp_path: Path) -> None:
    """Absent generator fails instead of returning an empty archive."""
    result = export_generator(_ctx(tmp_path), 'absent')

    assert isinstance(result, ToolFailure)


def test_export_escaping_name(tmp_path: Path) -> None:
    """Name escaping the generators root fails."""
    result = export_generator(_ctx(tmp_path / 'generators'), '../outside')

    assert isinstance(result, ToolFailure)


def test_export_over_inline_limit(tmp_path: Path, monkeypatch) -> None:
    """Archive above the limit is refused in favour of the REST API.

    Packing stops at the limit, so the failure names the limit alone -
    the size of an archive never finished is not known.
    """
    _gen(tmp_path)
    monkeypatch.setattr(archives, 'MAX_INLINE_ARCHIVE_SIZE', 1)

    result = export_generator(_ctx(tmp_path), 'g')

    assert isinstance(result, ToolFailure)
    assert result.details == {'name': 'g', 'limit': 1}


def test_import_creates_generator(tmp_path: Path) -> None:
    """Archive content is unpacked into a new generator directory."""
    content = _encoded_archive(
        {'generator.yml': 'input: []', 'templates/a.jinja': 'hi'},
    )

    result = import_generator(_ctx(tmp_path), 'imported', content)

    assert not isinstance(result, ToolFailure)
    assert result == {'imported': 'imported', 'files': 2}
    assert (tmp_path / 'imported' / 'generator.yml').read_text() == 'input: []'


def test_import_strips_wrapping_directory(tmp_path: Path) -> None:
    """Project nested in the archive is unpacked without the wrapper."""
    content = _encoded_archive({'web-nginx/generator.yml': 'input: []'})

    import_generator(_ctx(tmp_path), 'imported', content)

    assert (tmp_path / 'imported' / 'generator.yml').is_file()


def test_import_leaves_no_staging_directory(tmp_path: Path) -> None:
    """Staging directory is removed once the import completes."""
    content = _encoded_archive({'generator.yml': 'input: []'})

    import_generator(_ctx(tmp_path), 'imported', content)

    assert [path.name for path in tmp_path.iterdir()] == ['imported']


def test_import_read_only(tmp_path: Path) -> None:
    """Read-only server refuses the import without touching the disk."""
    content = _encoded_archive({'generator.yml': 'input: []'})

    result = import_generator(_ctx(tmp_path, read_only=True), 'g', content)

    assert isinstance(result, ToolFailure)
    assert not (tmp_path / 'g').exists()


def test_import_existing_generator(tmp_path: Path) -> None:
    """Existing generator is never overwritten."""
    _gen(tmp_path)
    content = _encoded_archive({'generator.yml': 'other: []'})

    result = import_generator(_ctx(tmp_path), 'g', content)

    assert isinstance(result, ToolFailure)
    assert (tmp_path / 'g' / 'generator.yml').read_text() == 'input: []\n'


def test_import_nested_name(tmp_path: Path) -> None:
    """Name must be a single directory name."""
    content = _encoded_archive({'generator.yml': 'input: []'})

    result = import_generator(_ctx(tmp_path), 'nested/name', content)

    assert isinstance(result, ToolFailure)


def test_import_invalid_base64(tmp_path: Path) -> None:
    """Content that is not base64 fails."""
    result = import_generator(_ctx(tmp_path), 'imported', 'not base64 !!')

    assert isinstance(result, ToolFailure)


def test_import_not_an_archive(tmp_path: Path) -> None:
    """Content that is not a ZIP archive fails and leaves nothing."""
    content = base64.b64encode(b'not an archive').decode('ascii')

    result = import_generator(_ctx(tmp_path), 'imported', content)

    assert isinstance(result, ToolFailure)
    assert list(tmp_path.iterdir()) == []


def test_import_without_configuration(tmp_path: Path) -> None:
    """Archive holding no generator configuration fails."""
    content = _encoded_archive({'templates/a.jinja': 'hi'})

    result = import_generator(_ctx(tmp_path), 'imported', content)

    assert isinstance(result, ToolFailure)


def test_import_over_inline_limit(tmp_path: Path, monkeypatch) -> None:
    """Content above the limit is refused in favour of the REST API."""
    monkeypatch.setattr(archives, 'MAX_INLINE_ARCHIVE_SIZE', 1)
    content = _encoded_archive({'generator.yml': 'input: []'})

    result = import_generator(_ctx(tmp_path), 'imported', content)

    assert isinstance(result, ToolFailure)
    assert result.details['limit'] == 1
    assert result.details['size'] > 1


def test_export_and_import_round_trip(tmp_path: Path) -> None:
    """A generator exported and imported back keeps its files."""
    _gen(tmp_path)
    context = _ctx(tmp_path)

    exported = export_generator(context, 'g')
    assert not isinstance(exported, ToolFailure)

    result = import_generator(context, 'copy', exported['content_base64'])

    assert not isinstance(result, ToolFailure)
    assert (tmp_path / 'copy' / 'templates' / 'a.jinja').read_text() == 'hi'
