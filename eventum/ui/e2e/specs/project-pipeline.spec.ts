import { expect, test } from '@playwright/test';

import {
  confirmDialog,
  createProject,
  inspector,
  selectStage,
} from '../helpers';

/**
 * The pipeline strip and the inspector beside it are how a generator is
 * assembled: what plugin runs at each stage and with what settings. The
 * configuration preview under the inspector is rendered from the same
 * draft the save writes, so it is what tells an edit that landed from
 * one that only redrew a field.
 */
test('the stages are switched and each names its plugin', async ({ page }) => {
  const project = await createProject(page, 'pipeline');

  await page.goto(`/projects/${project}`);

  for (const [stage, plugin] of [
    ['Input', 'timer'],
    ['Event', 'template'],
    ['Output', 'file'],
  ] as const) {
    await selectStage(page, stage);

    await expect(
      page.getByText(`INSPECTOR · ${stage.toUpperCase()}`)
    ).toBeVisible();
    await expect(inspector(page).getByText(`${plugin} #1`)).toBeVisible();
  }
});

test('a second input plugin is added and removed again', async ({ page }) => {
  const project = await createProject(page, 'add-plugin');

  await page.goto(`/projects/${project}`);
  await inspector(page).getByRole('button', { name: 'Add new plugin' }).click();

  await page.getByRole('button', { name: /^Cron\b/ }).click();

  // Both plugins now feed the stage, and the strip names what the stage
  // runs - two plugins are no longer named after one of them.
  await expect(inspector(page).getByText('cron #2')).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Input stage, timer +1' })
  ).toBeVisible();

  // Each plugin row carries a remove of its own, so the one being
  // removed is reached through the row that names it.
  // The label sits inside the body of the row and the remove beside
  // that body, so the row itself is two levels up from the name.
  const row = inspector(page).getByText('cron #2').locator('../..');
  await row.getByRole('button', { name: 'Remove' }).click();
  await confirmDialog(page, 'Delete');

  await expect(inspector(page).getByText('cron #2')).toHaveCount(0);
});

test('an edit reaches the configuration the save would write', async ({
  page,
}) => {
  const project = await createProject(page, 'edit-config');

  await page.goto(`/projects/${project}`);

  const seconds = inspector(page).getByRole('textbox', { name: 'Seconds' });
  await seconds.fill('42');

  // The preview is generated from the draft, so the value shows there
  // only once the form has handed the edit over.
  await expect(inspector(page).getByText('seconds: 42')).toBeVisible();

  await page.getByRole('button', { name: 'Save', exact: true }).click();
  await expect(page.getByText('Project configuration saved')).toBeVisible();

  await page.reload();
  // The field carries its unit, so the value reads back with it.
  await expect(
    inspector(page).getByRole('textbox', { name: 'Seconds' })
  ).toHaveValue('42 s.');
});

test('a required value left empty is marked as missing', async ({ page }) => {
  const project = await createProject(page, 'invalid-config');

  await page.goto(`/projects/${project}`);

  const seconds = inspector(page).getByRole('textbox', { name: 'Seconds' });
  await seconds.fill('');

  // The interval is what the plugin runs on, so an empty field is not a
  // configuration the form lets pass unmarked.
  await expect(seconds).toHaveAttribute('aria-invalid', 'true');

  // The studio does not hold the save back - the backend is what decides
  // what a plugin takes, and it says so.
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  await expect(page.getByText('Failed to save configuration')).toBeVisible();
});

test('leaving with an unsaved edit asks first', async ({ page }) => {
  const project = await createProject(page, 'guard');

  await page.goto(`/projects/${project}`);
  await inspector(page).getByRole('textbox', { name: 'Seconds' }).fill('7');

  await page.getByRole('button', { name: 'Back to projects' }).click();

  const dialog = page.getByRole('dialog');
  await expect(
    dialog.getByRole('heading', { name: 'Unsaved changes' })
  ).toBeVisible();

  await dialog.getByRole('button', { name: 'Stay' }).click();
  await expect(page).toHaveURL(new RegExp(`/projects/${project}$`));

  await page.getByRole('button', { name: 'Back to projects' }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Leave' }).click();
  await expect(page).toHaveURL(/\/projects$/);
});
