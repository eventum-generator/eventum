import { Completion } from '@codemirror/autocomplete';
import { describe, expect, it } from 'vitest';

import { getCompletions } from './globals';

/** The names offered under a path. */
function labels(...path: string[]): string[] {
  return getCompletions(path).map((completion) => completion.label);
}

/** Every completion the list holds, at every depth it can be walked to. */
function walk(): Completion[] {
  const all: Completion[] = [];

  const visit = (path: string[], depth: number) => {
    if (depth > 4) {
      return;
    }

    for (const completion of getCompletions(path)) {
      const next = [...path, completion.label];

      all.push(completion);

      // An unknown name falls back to the names of its parent, so a
      // walk that follows it would never end - only a name that leads
      // somewhere new is followed.
      const members = getCompletions(next);
      const parent = getCompletions(path).map((item) => item.label);
      const sameAsParent =
        members.length === parent.length &&
        members.every((item, index) => item.label === parent[index]);

      if (members.length > 0 && !sameAsParent) {
        visit(next, depth + 1);
      }
    }
  };

  visit([], 0);

  return all;
}

/**
 * The editor offers what a template can reach: the context it is
 * rendered with, the modules under it, and their members. The list is
 * written by hand against the template plugin, so what is checked here
 * is that it stays usable - every entry says what it is, every function
 * says how it is called, and a name that is offered can be walked into.
 */
describe('template completions', () => {
  it('offers the context every template is rendered with', () => {
    expect(labels()).toEqual(
      expect.arrayContaining([
        'timestamp',
        'tags',
        'params',
        'samples',
        'locals',
        'shared',
        'globals',
        'module',
        'dispatch',
        'subprocess',
      ])
    );
  });

  it('names what each entry is', () => {
    for (const completion of walk()) {
      expect(completion.type, completion.label).toBeTruthy();
      expect(completion.detail, completion.label).toBeTruthy();
    }
  });

  it('offers no name twice at one level', () => {
    const top = labels();

    expect(new Set(top).size).toBe(top.length);
  });

  it('offers the members of every state scope', () => {
    for (const scope of ['locals', 'shared', 'globals']) {
      expect(labels(scope), scope).toEqual(
        expect.arrayContaining(['get', 'set', 'pop', 'update', 'clear'])
      );
    }
  });

  it('offers the lock only on the scope that has one', () => {
    // Only the process-wide scope is shared between generators, so only
    // it can be held.
    expect(labels('globals')).toContain('acquire');
    expect(labels('shared')).not.toContain('acquire');
  });

  it('offers the modules a template can reach', () => {
    expect(labels('module')).toEqual(
      expect.arrayContaining(['rand', 'faker', 'mimesis'])
    );
  });

  it('offers the namespaces of the random module', () => {
    expect(labels('module', 'rand')).toEqual(
      expect.arrayContaining([
        'number',
        'string',
        'network',
        'crypto',
        'datetime',
        'choice',
        'weighted_choice',
        'chance',
      ])
    );
  });

  it('offers the flow controls a template can end on', () => {
    expect(labels('dispatch')).toEqual(
      expect.arrayContaining(['drop', 'next', 'exhaust'])
    );
  });

  it('names how every function it offers is called', () => {
    const functions = walk().filter(
      (completion) => completion.type === 'function'
    );

    expect(functions.length).toBeGreaterThan(20);

    for (const completion of functions) {
      // The signature is what the editor shows beside the name, and a
      // function offered without one says nothing about how to call it.
      expect(completion.info, completion.label).toMatch(/\([^()]{0,200}\)/);
    }
  });

  // A name the list does not know falls back to the level above it
  // rather than to nothing, so the editor keeps offering the context
  // after an unknown member. Recorded as it behaves.
  it('falls back to the level above for a name it does not know', () => {
    expect(labels('nonesuch')).toEqual(labels());
    expect(labels('module', 'nonesuch')).toEqual(labels('module'));
  });
});
