import { describe, expect, it } from 'vitest';

import { proposeProjectName } from './project-name';

describe('proposeProjectName', () => {
  it('proposes the name of the generator when it is free', () => {
    expect(proposeProjectName('web-nginx', [])).toBe('web-nginx');
  });

  it('folds what a project name cannot hold', () => {
    expect(proposeProjectName('web.nginx/logs', [])).toBe('web-nginx-logs');
  });

  it('steps aside from a name the workspace holds', () => {
    expect(proposeProjectName('web-nginx', ['web-nginx'])).toBe('web-nginx-2');
  });

  it('keeps stepping until the name is free', () => {
    expect(proposeProjectName('web-nginx', ['web-nginx', 'web-nginx-2'])).toBe(
      'web-nginx-3'
    );
  });
});
