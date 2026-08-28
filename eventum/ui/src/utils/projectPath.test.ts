import { describe, expect, it } from 'vitest';

import { projectOfConfig } from './projectPath';

/**
 * The instance pages name a project by the path of its configuration,
 * and link to it. A path that is no project of this workspace must not
 * be turned into a link that leads nowhere, and the name must stay a
 * name rather than growing into the whole path.
 */
describe('projectOfConfig', () => {
  it('names the project a workspace configuration sits in', () => {
    expect(projectOfConfig('web/generator.yml')).toEqual({
      name: 'web',
      inWorkspace: true,
    });
  });

  it('keeps a non-default configuration filename out of the name', () => {
    expect(projectOfConfig('web/nginx.yml').name).toBe('web');
  });

  it('takes the directory name of an out-of-tree configuration', () => {
    expect(projectOfConfig('/opt/eventum/web/generator.yml')).toEqual({
      name: 'web',
      inWorkspace: false,
    });
  });

  it.each([
    ['a path pointing outside the workspace', '../shared/web/generator.yml'],
    ['a path nested below a project', 'web/nested/generator.yml'],
    ['a configuration at the workspace root', 'generator.yml'],
  ])('reports %s as no project of the workspace', (_label, path) => {
    expect(projectOfConfig(path).inWorkspace).toBe(false);
  });
});
