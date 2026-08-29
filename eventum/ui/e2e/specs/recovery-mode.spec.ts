import { APIRequestContext, expect, test } from '@playwright/test';

import { createProject } from '../helpers';

/** Overwrite a file inside a project directory. */
async function putFile(
  request: APIRequestContext,
  projectName: string,
  filepath: string,
  content: string
): Promise<void> {
  const response = await request.put(
    `/api/generator-configs/${projectName}/file/${filepath}`,
    {
      multipart: {
        content: {
          name: filepath,
          mimeType: 'text/plain',
          buffer: Buffer.from(content),
        },
      },
    }
  );

  expect(response.ok()).toBeTruthy();
}

/**
 * A project left behind with a configuration nothing can parse would sit
 * in the workspace for every spec that runs after this file. One backend
 * serves them all, so this spec takes its own away.
 */
async function deleteProject(
  request: APIRequestContext,
  projectName: string
): Promise<void> {
  await request.delete(`/api/generator-configs/${projectName}`);
}

/**
 * A configuration the backend cannot parse must not lock the project
 * out: the studio opens in recovery mode with the file editor, which is
 * the only way left to repair the file that caused it.
 */
test('an unparseable configuration opens in recovery mode', async ({
  page,
  request,
}) => {
  const name = await createProject(page, 'recovery');

  await putFile(request, name, 'generator.yml', 'input: [ this: is: broken\n');

  await page.goto(`/projects/${name}`);

  await expect(
    page.getByText('Generator configuration is invalid')
  ).toBeVisible();

  // Recovery mode drops the pipeline and the inspector and keeps the
  // command bar with a reload, so the stage buttons must be gone.
  await expect(page.getByRole('button', { name: 'Input stage' })).toHaveCount(
    0
  );
  await expect(page.getByRole('button', { name: 'Reload' })).toBeVisible();

  // The editor and the file tree beside it are the whole point: without
  // them the file that locked the project out cannot be reached at all.
  await expect(page.locator('.studio-explorer')).toBeVisible();
  await expect(page.locator('.studio-editor')).toBeVisible();
  await expect(page.getByText('generator.yml')).toBeVisible();

  // Saving the config while in recovery mode would overwrite the broken
  // but real file with a placeholder, so no save is offered at all.
  await expect(page.getByRole('button', { name: 'Save' })).toHaveCount(0);

  await deleteProject(request, name);
});

test('a repaired configuration leaves recovery mode', async ({
  page,
  request,
}) => {
  const name = await createProject(page, 'repair');

  await putFile(request, name, 'generator.yml', 'input: [ this: is: broken\n');

  await page.goto(`/projects/${name}`);
  await expect(
    page.getByText('Generator configuration is invalid')
  ).toBeVisible();

  await putFile(
    request,
    name,
    'generator.yml',
    // The project was created with these assets, so this is the
    // configuration the studio started from.
    [
      'input:',
      '  - timer:',
      '      seconds: 5',
      '      count: 1',
      'event:',
      '  template:',
      '    mode: all',
      '    templates:',
      '      - template:',
      '          template: ./templates/template.jinja',
      'output:',
      '  - file:',
      '      path: ./output/output.log',
      '',
    ].join('\n')
  );

  await page.getByRole('button', { name: 'Reload' }).click();

  await expect(
    page.getByText('Generator configuration is invalid')
  ).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Input stage' })).toBeVisible();

  await deleteProject(request, name);
});
