"""Tests for project archive packing and unpacking."""

import io
import stat
import zipfile
from datetime import datetime
from pathlib import Path

import pytest

from eventum.app import archiving
from eventum.app.archiving import (
    ArchiveContentError,
    ArchiveError,
    iter_project_archive,
    unpack_project,
)

CONFIG_FILENAME = 'generator.yml'


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Project directory with a config, an asset and an output file."""
    path = tmp_path / 'project'
    (path / 'templates').mkdir(parents=True)
    (path / 'output').mkdir()

    (path / CONFIG_FILENAME).write_text('input: []\n', encoding='utf-8')
    (path / 'templates' / 'event.jinja').write_text('{}', encoding='utf-8')
    (path / 'output' / 'events.log').write_text('event', encoding='utf-8')

    return path


def _pack(project_dir: Path, destination: Path, **kwargs) -> None:
    """Collect a packed project into a file."""
    with destination.open('wb') as f:
        for chunk in iter_project_archive(project_dir, **kwargs):
            f.write(chunk)


def _archive_names(path: Path) -> set[str]:
    with zipfile.ZipFile(path) as archive:
        return {name.rstrip('/') for name in archive.namelist()}


def _build_archive(entries: dict[str, str]) -> io.BytesIO:
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, mode='w') as archive:
        for name, content in entries.items():
            archive.writestr(name, content)

    buffer.seek(0)
    return buffer


# --- packing ---


def test_pack_stores_paths_relative_to_project(project_dir, tmp_path):
    destination = tmp_path / 'project.zip'

    _pack(project_dir, destination)

    assert _archive_names(destination) == {
        CONFIG_FILENAME,
        'templates',
        'templates/event.jinja',
        'output',
        'output/events.log',
    }


def test_pack_excludes_named_top_level_entries(project_dir, tmp_path):
    destination = tmp_path / 'project.zip'

    _pack(project_dir, destination, exclude=['output'])

    assert _archive_names(destination) == {
        CONFIG_FILENAME,
        'templates',
        'templates/event.jinja',
    }


def test_pack_keeps_empty_directories(project_dir, tmp_path):
    (project_dir / 'samples').mkdir()
    destination = tmp_path / 'project.zip'

    _pack(project_dir, destination)

    assert 'samples' in _archive_names(destination)


def test_pack_skips_symlinks(project_dir, tmp_path):
    outside = tmp_path / 'secret.txt'
    outside.write_text('secret', encoding='utf-8')
    (project_dir / 'link.txt').symlink_to(outside)

    destination = tmp_path / 'project.zip'
    _pack(project_dir, destination)

    assert 'link.txt' not in _archive_names(destination)


def test_pack_missing_project(tmp_path):
    with pytest.raises(ArchiveError):
        _pack(tmp_path / 'absent', tmp_path / 'project.zip')


def test_pack_keeps_modification_times(project_dir, tmp_path):
    destination = tmp_path / 'project.zip'

    _pack(project_dir, destination)

    with zipfile.ZipFile(destination) as archive:
        packed = archive.getinfo(CONFIG_FILENAME).date_time

    # ZIP stores local time, which is what `datetime.fromtimestamp`
    # returns without a timezone.
    modified = datetime.fromtimestamp(  # noqa: DTZ006
        (project_dir / CONFIG_FILENAME).stat().st_mtime,
    )

    assert packed[:5] == (
        modified.year,
        modified.month,
        modified.day,
        modified.hour,
        modified.minute,
    )


# --- iter_project_archive ---


def test_iter_yields_the_archive_in_chunks(project_dir, tmp_path):
    # A project is packed without ever holding the archive whole, so
    # the content arrives as several chunks rather than one.
    (project_dir / 'samples').mkdir()
    (project_dir / 'samples' / 'big.csv').write_text('x' * 500_000)

    chunks = [chunk for chunk in iter_project_archive(project_dir) if chunk]
    content = b''.join(chunks)

    assert len(chunks) > 1

    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        assert archive.testzip() is None
        assert {name.rstrip('/') for name in archive.namelist()} == {
            CONFIG_FILENAME,
            'templates',
            'templates/event.jinja',
            'output',
            'output/events.log',
            'samples',
            'samples/big.csv',
        }
        assert len(archive.read('samples/big.csv')) == 500_000


def test_iter_missing_project(tmp_path):
    with pytest.raises(ArchiveError):
        list(iter_project_archive(tmp_path / 'absent'))


# --- unpack_project ---


def test_unpack_flat_archive(tmp_path):
    archive = _build_archive(
        {
            CONFIG_FILENAME: 'input: []',
            'templates/event.jinja': '{}',
        },
    )
    destination = tmp_path / 'unpacked'

    written = unpack_project(archive, destination, CONFIG_FILENAME)

    assert written == 2
    assert (destination / CONFIG_FILENAME).read_text() == 'input: []'
    assert (destination / 'templates' / 'event.jinja').read_text() == '{}'


def test_unpack_strips_wrapping_directory(tmp_path):
    archive = _build_archive(
        {
            'web-nginx/' + CONFIG_FILENAME: 'input: []',
            'web-nginx/templates/event.jinja': '{}',
        },
    )
    destination = tmp_path / 'unpacked'

    unpack_project(archive, destination, CONFIG_FILENAME)

    assert (destination / CONFIG_FILENAME).is_file()
    assert not (destination / 'web-nginx').exists()


def test_unpack_strips_nested_directories(tmp_path):
    archive = _build_archive(
        {
            'content-packs/generators/web/' + CONFIG_FILENAME: 'input: []',
            'content-packs/README.md': 'readme',
        },
    )
    destination = tmp_path / 'unpacked'

    written = unpack_project(archive, destination, CONFIG_FILENAME)

    assert written == 1
    assert (destination / CONFIG_FILENAME).is_file()
    assert not (destination / 'README.md').exists()


def test_unpack_takes_shallowest_configuration(tmp_path):
    archive = _build_archive(
        {
            CONFIG_FILENAME: 'input: []',
            'nested/' + CONFIG_FILENAME: 'input: []',
        },
    )
    destination = tmp_path / 'unpacked'

    unpack_project(archive, destination, CONFIG_FILENAME)

    assert (destination / 'nested' / CONFIG_FILENAME).is_file()


def test_unpack_without_configuration(tmp_path):
    archive = _build_archive({'templates/event.jinja': '{}'})

    with pytest.raises(ArchiveContentError):
        unpack_project(archive, tmp_path / 'unpacked', CONFIG_FILENAME)


def test_unpack_with_several_configurations(tmp_path):
    archive = _build_archive(
        {
            'first/' + CONFIG_FILENAME: 'input: []',
            'second/' + CONFIG_FILENAME: 'input: []',
        },
    )

    with pytest.raises(ArchiveContentError):
        unpack_project(archive, tmp_path / 'unpacked', CONFIG_FILENAME)


def test_unpack_rejects_absolute_entry(tmp_path):
    archive = _build_archive(
        {
            CONFIG_FILENAME: 'input: []',
            '/etc/passwd': 'root',
        },
    )

    with pytest.raises(ArchiveContentError):
        unpack_project(archive, tmp_path / 'unpacked', CONFIG_FILENAME)


def test_unpack_rejects_parent_traversal(tmp_path):
    archive = _build_archive(
        {
            CONFIG_FILENAME: 'input: []',
            '../escaped.txt': 'escaped',
        },
    )

    with pytest.raises(ArchiveContentError):
        unpack_project(archive, tmp_path / 'unpacked', CONFIG_FILENAME)


def test_unpack_rejects_symlink_entry(tmp_path):
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, mode='w') as archive:
        archive.writestr(CONFIG_FILENAME, 'input: []')

        link = zipfile.ZipInfo('link.txt')
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(link, '/etc/passwd')

    buffer.seek(0)

    with pytest.raises(ArchiveContentError):
        unpack_project(buffer, tmp_path / 'unpacked', CONFIG_FILENAME)


def test_unpack_rejects_too_many_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(archiving, 'MAX_ARCHIVE_ENTRIES', 1)
    archive = _build_archive(
        {CONFIG_FILENAME: 'input: []', 'note.txt': 'note'},
    )

    with pytest.raises(ArchiveContentError):
        unpack_project(archive, tmp_path / 'unpacked', CONFIG_FILENAME)


def test_unpack_rejects_declared_size_over_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(archiving, 'MAX_UNPACKED_SIZE', 4)
    archive = _build_archive({CONFIG_FILENAME: 'input: []'})

    with pytest.raises(ArchiveContentError):
        unpack_project(archive, tmp_path / 'unpacked', CONFIG_FILENAME)


def test_unpack_rejects_written_size_over_limit(tmp_path, monkeypatch):
    # An archive is free to understate the size of its entries, so the
    # limit is enforced again while the content is written.
    monkeypatch.setattr(archiving, '_validate_entries', lambda entries: None)
    monkeypatch.setattr(archiving, 'MAX_UNPACKED_SIZE', 4)
    archive = _build_archive({CONFIG_FILENAME: 'input: []'})

    with pytest.raises(ArchiveContentError):
        unpack_project(archive, tmp_path / 'unpacked', CONFIG_FILENAME)


def test_unpack_skips_finder_metadata(tmp_path):
    archive = _build_archive(
        {
            CONFIG_FILENAME: 'input: []',
            '__MACOSX/._' + CONFIG_FILENAME: 'metadata',
        },
    )
    destination = tmp_path / 'unpacked'

    written = unpack_project(archive, destination, CONFIG_FILENAME)

    assert written == 1
    assert not (destination / '__MACOSX').exists()


def test_unpack_not_an_archive(tmp_path):
    with pytest.raises(ArchiveContentError):
        unpack_project(
            io.BytesIO(b'not an archive'),
            tmp_path / 'unpacked',
            CONFIG_FILENAME,
        )


def test_pack_and_unpack_round_trip(project_dir, tmp_path):
    destination = tmp_path / 'project.zip'
    _pack(project_dir, destination)

    unpacked = tmp_path / 'unpacked'

    with destination.open('rb') as f:
        written = unpack_project(f, unpacked, CONFIG_FILENAME)

    assert written == 3
    assert (unpacked / CONFIG_FILENAME).read_text() == 'input: []\n'
    assert (unpacked / 'templates' / 'event.jinja').read_text() == '{}'
    assert (unpacked / 'output' / 'events.log').read_text() == 'event'
