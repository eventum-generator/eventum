import { describe, expect, it } from 'vitest';

import { proposeRepositoryName } from './repository-name';

describe('proposeRepositoryName', () => {
  it('offers the name the repository carries', () => {
    expect(proposeRepositoryName('content-packs', [])).toBe('content-packs');
  });

  it('folds what a name may not hold', () => {
    expect(proposeRepositoryName('my packs!', [])).toBe('my-packs');
  });

  it('cuts what a name may not begin or end with', () => {
    expect(proposeRepositoryName('.packs.', [])).toBe('packs');
  });

  it('offers a free name when the first one is taken', () => {
    expect(proposeRepositoryName('packs', ['packs', 'packs-2'])).toBe(
      'packs-3'
    );
  });

  it('offers nothing for a name that folds to nothing', () => {
    expect(proposeRepositoryName('...', [])).toBe('');
  });
});
