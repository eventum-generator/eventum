import { describe, expect, it } from 'vitest';

import { FileNode } from '../../schemas';
import { createFileTreeLookup, findFileNode, flattenFileTree } from './index';

function dir(name: string, children: FileNode[]): FileNode {
  return { name, is_dir: true, size_in_bytes: null, children };
}

function file(name: string, size = 1): FileNode {
  return { name, is_dir: false, size_in_bytes: size, children: null };
}

// Deliberately unsorted and mixed in case, since the tree arrives in
// whatever order the backend walked the directory in.
const TREE: FileNode[] = [
  file('generator.yml'),
  dir('templates', [
    file('main.jinja'),
    dir('macros', [file('base.jinja')]),
    file('Alt.jinja'),
  ]),
  dir('samples', [file('users.csv')]),
];

/**
 * The explorer draws the project directory, and both the tree and the
 * flat list are built from these. The order is what the user reads, so
 * it has to be the same wherever the tree appears: directories first,
 * then names compared without regard to case.
 */
describe('flattenFileTree', () => {
  it('puts directories before files and sorts each group by name', () => {
    expect(flattenFileTree(TREE, false)).toEqual([
      'samples',
      'samples/users.csv',
      'templates',
      'templates/macros',
      'templates/macros/base.jinja',
      'templates/Alt.jinja',
      'templates/main.jinja',
      'generator.yml',
    ]);
  });

  it('leaves the directories out when only files were asked for', () => {
    expect(flattenFileTree(TREE, true)).toEqual([
      'samples/users.csv',
      'templates/macros/base.jinja',
      'templates/Alt.jinja',
      'templates/main.jinja',
      'generator.yml',
    ]);
  });

  it('compares names without regard to case', () => {
    const paths = flattenFileTree(
      [dir('d', [file('b.txt'), file('A.txt')])],
      true
    );

    expect(paths).toEqual(['d/A.txt', 'd/b.txt']);
  });

  it('keeps an empty directory in the list', () => {
    expect(flattenFileTree([dir('output', [])], false)).toEqual(['output']);
  });

  it('returns nothing for an empty tree', () => {
    expect(flattenFileTree([], false)).toEqual([]);
  });
});

describe('findFileNode', () => {
  it('finds a file nested more than one level deep', () => {
    expect(findFileNode(TREE, 'templates/macros/base.jinja')?.is_dir).toBe(
      false
    );
  });

  it('finds a directory by its path', () => {
    expect(findFileNode(TREE, 'templates')?.name).toBe('templates');
  });

  it('finds nothing for a path that does not exist', () => {
    expect(findFileNode(TREE, 'templates/missing.jinja')).toBeUndefined();
  });

  it('finds nothing when a segment along the way is a file', () => {
    expect(findFileNode(TREE, 'generator.yml/nested')).toBeUndefined();
  });
});

describe('createFileTreeLookup', () => {
  it('keys every node by its full path', () => {
    const { items } = createFileTreeLookup(TREE);

    expect(items.get('templates/macros/base.jinja')?.name).toBe('base.jinja');
    expect([...items.keys()]).toHaveLength(8);
  });

  it('lists the root children under the empty path', () => {
    const { children } = createFileTreeLookup(TREE);

    expect(children.get('')).toEqual(['samples', 'templates', 'generator.yml']);
  });

  it('sorts the children of a directory the same way the list is sorted', () => {
    const { children } = createFileTreeLookup(TREE);

    expect(children.get('templates')).toEqual([
      'templates/macros',
      'templates/Alt.jinja',
      'templates/main.jinja',
    ]);
  });

  it('gives a directory with no children an empty entry, not a missing one', () => {
    const { children } = createFileTreeLookup([dir('output', [])]);

    expect(children.get('output')).toEqual([]);
  });

  it('gives a file no children entry at all', () => {
    const { children } = createFileTreeLookup([file('generator.yml')]);

    expect(children.has('generator.yml')).toBe(false);
  });
});
