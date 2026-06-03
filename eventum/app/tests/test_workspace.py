"""Tests for transport-neutral generator-workspace helper."""

import os
from pathlib import Path

import pytest

from eventum.app.workspace import (
    WorkspaceError,
    ensure_relative,
    read_text,
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


def test_read_text_missing_path_raises(tmp_path: Path):
    missing = tmp_path / 'nope.txt'
    with pytest.raises(WorkspaceError) as exc_info:
        read_text(missing)
    assert exc_info.value.context['file_path'] == str(missing)


def test_write_text_parent_is_file_raises(tmp_path: Path):
    blocker = tmp_path / 'blocker'
    blocker.write_text('x')
    target = blocker / 'child.txt'
    with pytest.raises(WorkspaceError) as exc_info:
        write_text(target, 'data')
    assert exc_info.value.context['file_path'] == str(target)
