import { expect, test } from '@playwright/test';

import { confirmDialog, createProject, uniqueName } from '../helpers';

/**
 * The explorer is the only way into the files of a project, and the
 * editor beside it is the only way to change one. Both act through the
 * backend on every step - a file created here is a file on disk - so
 * each check reads the result back from a reloaded page rather than from
 * the tree the studio is still holding.
 */
test('a file is created, edited, saved and deleted', async ({ page }) => {
  const project = await createProject(page, 'explorer');
  const filename = `${uniqueName('note')}.txt`;

  await page.goto(`/projects/${project}`);

  await page.getByRole('button', { name: 'New file' }).click();
  await page.getByPlaceholder('path').fill(filename);
  await page.getByRole('button', { name: 'Create', exact: true }).click();

  const explorer = page.locator('.studio-explorer');
  await expect(explorer.getByText(filename)).toBeVisible();

  // Opening the file puts it in the editor, which is where the content
  // is typed and saved from.
  await explorer.getByText(filename).click();

  const editor = page.locator('.studio-editor');
  await expect(editor.getByText(filename)).toBeVisible();

  await editor.locator('.cm-content').click();
  await page.keyboard.type('written by the browser suite');
  await page.getByRole('button', { name: 'Save', exact: true }).click();

  // A reload drops everything the studio held, so what is shown after
  // it came from the file.
  await page.reload();
  await page.locator('.studio-explorer').getByText(filename).click();
  await expect(
    page.locator('.studio-editor').getByText('written by the browser suite')
  ).toBeVisible();

  await page
    .locator('.studio-explorer')
    .getByText(filename)
    .click({ button: 'right' });
  await page.getByRole('button', { name: 'Delete' }).click();
  await confirmDialog(page, 'Delete');

  await expect(
    page.locator('.studio-explorer').getByText(filename)
  ).toHaveCount(0);
});

test('a folder is created and holds a file', async ({ page }) => {
  const project = await createProject(page, 'explorer-dir');
  const folder = uniqueName('samples');

  await page.goto(`/projects/${project}`);

  await page.getByRole('button', { name: 'New folder' }).click();
  await page.getByPlaceholder('path').fill(folder);
  await page.getByRole('button', { name: 'Create', exact: true }).click();

  const explorer = page.locator('.studio-explorer');
  await expect(explorer.getByText(folder)).toBeVisible();

  // A path with separators creates the directories it names, so the
  // file lands inside the folder rather than beside it.
  await page.getByRole('button', { name: 'New file' }).click();
  await page.getByPlaceholder('path').fill(`${folder}/hosts.csv`);
  await page.getByRole('button', { name: 'Create', exact: true }).click();

  await explorer.getByText(folder).click();
  await expect(explorer.getByText('hosts.csv')).toBeVisible();
});

test('a file is renamed in place', async ({ page }) => {
  const project = await createProject(page, 'explorer-rename');
  const filename = `${uniqueName('before')}.txt`;

  await page.goto(`/projects/${project}`);
  await page.getByRole('button', { name: 'New file' }).click();
  await page.getByPlaceholder('path').fill(filename);
  await page.getByRole('button', { name: 'Create', exact: true }).click();

  const explorer = page.locator('.studio-explorer');
  await explorer.getByText(filename).click({ button: 'right' });
  await page.getByRole('button', { name: 'Rename' }).click();

  // Renaming happens in the tree itself: the name turns into a field,
  // and Enter is what commits it.
  await explorer.getByRole('textbox').fill('after.txt');
  await explorer.getByRole('textbox').press('Enter');

  await expect(explorer.getByText('after.txt')).toBeVisible();
  await expect(explorer.getByText(filename)).toHaveCount(0);

  // The tree is redrawn from the project, so a reload is what tells a
  // renamed file from a relabelled row.
  await page.reload();
  await expect(
    page.locator('.studio-explorer').getByText('after.txt')
  ).toBeVisible();
});

test('the configuration file cannot be deleted from the explorer', async ({
  page,
}) => {
  const project = await createProject(page, 'explorer-guard');

  await page.goto(`/projects/${project}`);
  await page
    .locator('.studio-explorer')
    .getByText('generator.yml')
    .click({ button: 'right' });

  // Losing it would take the project down with it, so the menu of that
  // one file offers no delete at all.
  await expect(page.getByRole('button', { name: 'Delete' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Download' })).toBeVisible();
});
