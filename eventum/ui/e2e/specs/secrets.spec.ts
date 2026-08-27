import { expect, test } from '@playwright/test';

import { confirmDialog, uniqueName } from '../helpers';

/**
 * A secret is held in the keyring and never served back with the rest of
 * the configuration - the page reads a value only when asked to. So what
 * matters is that adding one stores it, that revealing it returns the
 * value that was stored, and that deleting one takes it out of the
 * keyring rather than only out of the table.
 */
test('a secret is added, revealed and deleted', async ({ page }) => {
  const name = uniqueName('secret');

  await page.goto('/secrets');
  await page.getByRole('button', { name: 'Add secret' }).click();

  await page.getByRole('textbox', { name: 'Name' }).fill(name);
  await page.getByRole('textbox', { name: 'Value' }).fill('s3cr3t-value');
  await page.getByRole('button', { name: 'Add', exact: true }).click();

  await expect(page.getByText('New secret was added')).toBeVisible();

  const row = page.getByRole('row').filter({ hasText: name });
  await expect(row).toHaveCount(1);

  // The value is masked until it is asked for, and the request is what
  // proves the keyring holds it.
  await expect(row.getByText('s3cr3t-value')).toHaveCount(0);
  await row.getByRole('button', { name: 'Show' }).click();
  await expect(row.getByText('s3cr3t-value')).toBeVisible();

  await row.getByRole('button', { name: 'Remove' }).click();
  await confirmDialog(page, 'Delete');

  await expect(page.getByText('Secret was deleted')).toBeVisible();
  await expect(page.getByRole('row').filter({ hasText: name })).toHaveCount(0);
});

test('a secret value is replaced by editing it', async ({ page }) => {
  const name = uniqueName('secret-edit');

  await page.goto('/secrets');
  await page.getByRole('button', { name: 'Add secret' }).click();
  await page.getByRole('textbox', { name: 'Name' }).fill(name);
  await page.getByRole('textbox', { name: 'Value' }).fill('first-value');
  await page.getByRole('button', { name: 'Add', exact: true }).click();
  await expect(page.getByText('New secret was added')).toBeVisible();

  const row = page.getByRole('row').filter({ hasText: name });
  await row.getByRole('button', { name: 'Edit' }).click();
  await row.getByPlaceholder('secret value').fill('second-value');
  await row.getByRole('button', { name: 'Save' }).click();

  await expect(page.getByText('Secret value was updated')).toBeVisible();

  // Reading it back is the only way to tell a stored value from one the
  // form is still holding, so the page is loaded afresh first.
  await page.reload();
  const reloaded = page.getByRole('row').filter({ hasText: name });
  await reloaded.getByRole('button', { name: 'Show' }).click();
  await expect(reloaded.getByText('second-value')).toBeVisible();

  await reloaded.getByRole('button', { name: 'Remove' }).click();
  await confirmDialog(page, 'Delete');
});

test('a secret is renamed and keeps its value', async ({ page }) => {
  const name = uniqueName('secret-rename');
  const renamed = `${name}-renamed`;

  await page.goto('/secrets');
  await page.getByRole('button', { name: 'Add secret' }).click();
  await page.getByRole('textbox', { name: 'Name' }).fill(name);
  await page.getByRole('textbox', { name: 'Value' }).fill('kept-value');
  await page.getByRole('button', { name: 'Add', exact: true }).click();
  await expect(page.getByText('New secret was added')).toBeVisible();

  await page
    .getByRole('row')
    .filter({ hasText: name })
    .getByRole('button', { name: 'Rename secret' })
    .click();

  const dialog = page.getByRole('dialog');
  await dialog.getByRole('textbox').fill(renamed);
  await dialog.getByRole('button', { name: /Rename/ }).click();

  const row = page.getByRole('row').filter({ hasText: renamed });
  await expect(row).toHaveCount(1);

  await row.getByRole('button', { name: 'Show' }).click();
  await expect(row.getByText('kept-value')).toBeVisible();

  await row.getByRole('button', { name: 'Remove' }).click();
  await confirmDialog(page, 'Delete');
});
