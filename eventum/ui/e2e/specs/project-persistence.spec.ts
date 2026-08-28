import { expect, test } from '@playwright/test';

import { createProject, inspector, openProject, selectStage } from '../helpers';

/**
 * A configuration edited in the inspector has to reach the file on
 * disk. The form holds its own copy of the values, so a save that never
 * happened, or a reload that re-reads a stale response, both look
 * exactly like a successful edit until the project is reopened.
 */
test('a plugin configuration survives a reopen', async ({ page }) => {
  const name = await createProject(page, 'persist');

  await openProject(page, name);
  await selectStage(page, 'Input');

  const count = inspector(page).getByRole('textbox', { name: 'Count' });
  await expect(count).toHaveValue('1');

  await count.fill('7');

  // The command bar only offers a save once it sees a change, so a
  // disabled button here means the edit never reached the config.
  const save = page.getByRole('button', { name: 'Save', exact: true });
  await expect(save).toBeEnabled();
  await save.click();

  await expect(page.getByText('Project configuration saved')).toBeVisible();

  await page.reload();
  await selectStage(page, 'Input');

  await expect(
    inspector(page).getByRole('textbox', { name: 'Count' })
  ).toHaveValue('7');
});

test('an unsaved edit is not written', async ({ page }) => {
  const name = await createProject(page, 'discard');

  await openProject(page, name);
  await selectStage(page, 'Input');

  await inspector(page).getByRole('textbox', { name: 'Count' }).fill('5');

  // Leaving with unsaved changes is guarded, so the prompt has to be
  // dismissed the way a user dismisses it.
  page.once('dialog', (dialog) => void dialog.accept());
  await page.goto(`/projects/${name}`);

  await selectStage(page, 'Input');
  await expect(
    inspector(page).getByRole('textbox', { name: 'Count' })
  ).toHaveValue('1');
});
