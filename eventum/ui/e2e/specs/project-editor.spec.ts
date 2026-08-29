import { expect, test } from '@playwright/test';

import { createProject, uniqueName } from '../helpers';

/**
 * The editor is where templates and scripts are written, and it carries
 * a search of its own - the one part of the studio that measures the
 * text it draws, which is why it is read here rather than in jsdom.
 */
test('the editor finds and counts what it is asked for', async ({ page }) => {
  const project = await createProject(page, 'editor-search');
  const filename = `${uniqueName('notes')}.txt`;

  await page.goto(`/projects/${project}`);

  await page.getByRole('button', { name: 'New file' }).click();
  await page.getByPlaceholder('path').fill(filename);
  await page.getByRole('button', { name: 'Create', exact: true }).click();

  const explorer = page.locator('.studio-explorer');
  await explorer.getByText(filename).click();

  const editor = page.locator('.studio-editor');
  await editor.locator('.cm-content').click();
  await page.keyboard.type('alpha beta alpha gamma alpha');

  await page.keyboard.press('ControlOrMeta+f');

  const search = editor.getByPlaceholder(/Find|Search/i).first();
  await expect(search).toBeVisible();
  await search.fill('alpha');

  // The panel counts what it found, which is what tells a search that
  // matched from one that did not.
  await expect(editor.getByText(/3/).first()).toBeVisible();

  await search.fill('nothing-here');
  await expect(editor.getByText(/No results|0 of 0|0\/0/i)).toBeVisible();

  await page.keyboard.press('Escape');
  await expect(search).toHaveCount(0);
});

test('an edited file is saved and read back', async ({ page }) => {
  const project = await createProject(page, 'editor-save');
  const filename = `${uniqueName('template')}.jinja`;

  await page.goto(`/projects/${project}`);

  await page.getByRole('button', { name: 'New file' }).click();
  await page.getByPlaceholder('path').fill(`templates/${filename}`);
  await page.getByRole('button', { name: 'Create', exact: true }).click();

  const explorer = page.locator('.studio-explorer');
  await explorer.getByText('templates').click();
  await explorer.getByText(filename).click();

  await page.locator('.studio-editor .cm-content').click();
  await page.keyboard.type('{{ timestamp }}');

  // The command bar counts what is unsaved, so it names the file rather
  // than only lighting up.
  await expect(page.getByText(/1 file/)).toBeVisible();

  await page.getByRole('button', { name: 'Save', exact: true }).click();
  await expect(page.getByText(/1 file/)).toHaveCount(0);

  await page.reload();
  await page.locator('.studio-explorer').getByText('templates').click();
  await page.locator('.studio-explorer').getByText(filename).click();
  await expect(
    page.locator('.studio-editor').getByText('{{ timestamp }}')
  ).toBeVisible();
});
