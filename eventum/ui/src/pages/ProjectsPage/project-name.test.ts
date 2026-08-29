import { describe, expect, it } from 'vitest';

import { projectNameFromArchive, validateProjectName } from './project-name';

describe('validateProjectName', () => {
  it('requires a name', () => {
    expect(validateProjectName('', [])).toBe('Project name is required');
  });

  it('rejects unsupported characters', () => {
    expect(validateProjectName('web nginx', [])).toMatch(/Only letters/);
  });

  it('rejects a taken name', () => {
    expect(validateProjectName('web', ['web'])).toMatch(/already exists/);
  });

  it('accepts letters, digits, dashes and underscores', () => {
    expect(validateProjectName('web-nginx_1', ['other'])).toBeNull();
  });
});

describe('projectNameFromArchive', () => {
  it('drops the extension', () => {
    expect(projectNameFromArchive('web-nginx.zip')).toBe('web-nginx');
  });

  it('keeps a name without extension', () => {
    expect(projectNameFromArchive('web-nginx')).toBe('web-nginx');
  });

  it('drops only the last extension', () => {
    expect(projectNameFromArchive('web-nginx.v2.zip')).toBe('web-nginx-v2');
  });

  it('folds unsupported characters into a dash', () => {
    expect(projectNameFromArchive('web nginx (1).zip')).toBe('web-nginx-1');
  });

  it('trims leading and trailing dashes', () => {
    expect(projectNameFromArchive(' web.zip ')).toBe('web');
  });

  it('yields an empty name when nothing is left', () => {
    expect(projectNameFromArchive('..zip')).toBe('');
  });
});
