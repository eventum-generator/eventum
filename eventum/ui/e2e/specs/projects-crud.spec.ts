import { expect, test } from '@playwright/test';

import {
  confirmDialog,
  createProject,
  openProjectActions,
  projectRow,
  uniqueName,
} from '../helpers';

/**
 * A project is a directory of the workspace, and what the table shows is
 * read off the filesystem rather than held anywhere. So each of these
 * goes through the studio and then reads the result back from the table
 * the next request fills.
 */
test.describe('creating a project', () => {
  for (const type of ['Template', 'Replay', 'Script'] as const) {
    test(`a ${type.toLowerCase()} project opens with its own assets`, async ({
      page,
    }) => {
      const name = await createProject(page, `new-${type}`, type);

      await page.goto(`/projects/${name}`);

      // The project type decides the event plugin the pipeline opens
      // with, and the assets that come with it.
      await expect(
        page.getByRole('button', { name: `Event stage, ${type.toLowerCase()}` })
      ).toBeVisible();
      await expect(page.locator('.studio-explorer')).toBeVisible();
    });
  }

  test('a name already taken is refused', async ({ page }) => {
    const name = await createProject(page, 'taken');

    await page.goto('/projects');
    await page
      .getByRole('button', { name: /^Create new( project)?$/ })
      .first()
      .click();
    await page.getByRole('button', { name: /^Template\b/ }).click();
    await page.getByRole('textbox', { name: 'Project name' }).fill(name);

    // The modal knows the names in use, so it refuses before asking the
    // backend - a second directory of the same name cannot exist.
    await expect(
      page.getByRole('button', { name: 'Create', exact: true })
    ).toBeDisabled();
  });
});

test('a project is renamed and keeps its files', async ({ page }) => {
  const name = await createProject(page, 'rename');
  const renamed = `${name}-renamed`;

  await openProjectActions(page, name);
  await page.getByRole('menuitem', { name: 'Rename' }).click();

  const dialog = page.getByRole('dialog');
  await expect(
    dialog.getByText('No instance uses this project.')
  ).toBeVisible();
  await dialog.getByRole('textbox', { name: 'New project name' }).fill(renamed);
  await dialog.getByRole('button', { name: 'Rename' }).click();

  await expect(page.getByText(`renamed to "${renamed}"`)).toBeVisible();

  // The directory moved rather than being copied, so the old name is
  // gone and the new one holds the project.
  await page.goto(`/projects/${name}`);
  await expect(page.getByText(/not found|Failed/i).first()).toBeVisible();

  await page.goto(`/projects/${renamed}`);
  await expect(page.getByRole('button', { name: 'Input stage' })).toBeVisible();
});

test('a project is packed into an archive', async ({ page }) => {
  const name = await createProject(page, 'export');

  await openProjectActions(page, name);
  await page.getByRole('menuitem', { name: 'Export' }).click();

  const dialog = page.getByRole('dialog');
  await expect(dialog.getByText('generator.yml')).toBeVisible();

  const download = page.waitForEvent('download');
  await dialog.getByRole('button', { name: 'Export' }).click();

  const file = await download;
  expect(file.suggestedFilename()).toMatch(/\.zip$/);
});

test('a project is deleted from the workspace', async ({ page }) => {
  const name = await createProject(page, 'delete');

  await openProjectActions(page, name);
  await page.getByRole('menuitem', { name: 'Delete' }).click();
  await confirmDialog(page, 'Delete');

  await page.goto('/projects');
  await page.getByPlaceholder('search by name...').fill(name);
  await expect(page.getByRole('row').filter({ hasText: name })).toHaveCount(0);
});

test('the table narrows to what the search asks for', async ({ page }) => {
  const name = await createProject(page, 'search');

  const row = await projectRow(page, name);
  await expect(row).toBeVisible();

  await page.getByPlaceholder('search by name...').fill(uniqueName('nothing'));
  await expect(page.getByRole('row').filter({ hasText: name })).toHaveCount(0);
});

test('a project with no instance is not listed as in use', async ({ page }) => {
  const name = await createProject(page, 'unused');

  await page.goto('/projects');

  // The filter hides its radios and draws labels over them, so the label
  // is what a user can click.
  await page.getByText('Unused', { exact: true }).click();
  await page.getByPlaceholder('search by name...').fill(name);
  await expect(page.getByRole('row').filter({ hasText: name })).toHaveCount(1);

  await page.getByText('In use', { exact: true }).click();
  await expect(page.getByRole('row').filter({ hasText: name })).toHaveCount(0);
});
