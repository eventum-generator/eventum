import { describe, expect, it } from 'vitest';

import {
  hasForeignToken,
  isReferenceable,
  isSecretReference,
  secretReference,
} from './secretReference';

describe('isSecretReference', () => {
  it.each([
    '${secrets.git_token}',
    '${ secrets.git_token }',
    '${secrets.git.token}',
  ])('reads %s as a reference', (value) => {
    expect(isSecretReference(value)).toBe(true);
  });

  it.each([
    undefined,
    '',
    'ghp_token',
    '${secrets.}',
    'prefix-${secrets.git_token}',
    '${secrets.git_token}-suffix',
    '${params.git_token}',
    // Padding belongs to the value, not to the token: the backend
    // substitutes inside it and keeps the spaces.
    '${secrets.git_token} ',
    ' ${secrets.git_token}',
  ])('reads %s as a value of its own', (value) => {
    expect(isSecretReference(value)).toBe(false);
  });
});

describe('hasForeignToken', () => {
  it.each([
    '${params.git_token}',
    '${git_token}',
    'a-${params.x}-b',
    '${secrets.}',
  ])('names %s as a token that is not substituted', (value) => {
    expect(hasForeignToken(value)).toBe(true);
  });

  it.each([
    'ghp_token',
    '${secrets.git_token}',
    'a-${secrets.x}-b',
    'p@$$w0rd',
  ])('leaves %s alone', (value) => {
    expect(hasForeignToken(value)).toBe(false);
  });
});

describe('isReferenceable', () => {
  it.each(['git_token', 'a.b', 'GIT-TOKEN_1'])(
    'writes %s as a reference',
    (name) => {
      expect(isReferenceable(name)).toBe(true);
    }
  );

  it.each(['my key', 'a}b', 'tab\there'])(
    'cannot write %s as a reference',
    (name) => {
      expect(isReferenceable(name)).toBe(false);
    }
  );
});

describe('secretReference', () => {
  it('writes the reference of a secret', () => {
    expect(secretReference('git_token')).toBe('${secrets.git_token}');
  });
});
