"""Tests for file tree builder."""

from eventum.api.routers.generator_configs.file_tree import build_file_tree


def test_single_file(tmp_path):
    f = tmp_path / 'test.txt'
    f.write_text('content')

    node = build_file_tree(f)
    assert node.name == 'test.txt'
    assert node.is_dir is False
    assert node.children is None


def test_empty_directory(tmp_path):
    d = tmp_path / 'empty'
    d.mkdir()

    node = build_file_tree(d)
    assert node.name == 'empty'
    assert node.is_dir is True
    assert node.children == []


def test_nested_structure(tmp_path):
    d = tmp_path / 'root'
    d.mkdir()
    (d / 'sub').mkdir()
    (d / 'sub' / 'file.txt').write_text('nested')

    node = build_file_tree(d)
    assert node.is_dir is True
    assert len(node.children) == 1  # type: ignore

    sub = node.children[0]  # type: ignore
    assert sub.name == 'sub'
    assert sub.is_dir is True
    assert len(sub.children) == 1  # type: ignore
    assert sub.children[0].name == 'file.txt'  # type: ignore
    assert sub.children[0].is_dir is False  # type: ignore


def test_mixed_files_and_dirs(tmp_path):
    d = tmp_path / 'project'
    d.mkdir()
    (d / 'config.yml').write_text('key: val')
    (d / 'templates').mkdir()
    (d / 'templates' / 'event.jinja').write_text('{{ timestamp }}')

    node = build_file_tree(d)
    assert node.is_dir is True
    assert len(node.children) == 2  # type: ignore

    names = {child.name for child in node.children}  # type: ignore
    assert names == {'config.yml', 'templates'}


def test_node_names_match_path(tmp_path):
    f = tmp_path / 'my_file.yml'
    f.write_text('')

    node = build_file_tree(f)
    assert node.name == 'my_file.yml'


def test_file_size(tmp_path):
    f = tmp_path / 'test.txt'
    f.write_bytes(b'content')

    node = build_file_tree(f)
    assert node.size_in_bytes == len(b'content')


def test_directory_size_is_unknown(tmp_path):
    d = tmp_path / 'project'
    d.mkdir()
    (d / 'test.txt').write_bytes(b'content')

    node = build_file_tree(d)
    assert node.size_in_bytes is None
    assert node.children[0].size_in_bytes == len(b'content')  # type: ignore


def test_unreadable_file_size_is_unknown(tmp_path):
    link = tmp_path / 'dangling.txt'
    link.symlink_to(tmp_path / 'missing.txt')

    node = build_file_tree(link)
    assert node.is_dir is False
    assert node.size_in_bytes is None
