import { expect, test } from '@playwright/test';

/**
 * The studio is served by the instance it manages, behind the basic auth
 * of that instance. These tests run without the stored session of the
 * rest of the suite: what they check is what happens before there is
 * one.
 */
test.use({ storageState: { cookies: [], origins: [] } });

test('an address of the studio asks to sign in first', async ({ page }) => {
  await page.goto('/instances');

  await expect(page).toHaveURL(/\/signin$/);
  await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible();
});

test('credentials that are not the ones configured are refused', async ({
  page,
}) => {
  await page.goto('/signin');

  await page.getByRole('textbox', { name: 'Username' }).fill('eventum');
  await page
    .getByRole('textbox', { name: 'Password' })
    .fill('not-the-password');
  await page.getByRole('button', { name: 'Sign In' }).click();

  // The page must stay: a wrong password that let the user through would
  // be the whole point of the check.
  await expect(page).toHaveURL(/\/signin$/);
  await expect(page.getByText(/Invalid|Failed|incorrect/i)).toBeVisible();
});

test('the configured credentials open the studio', async ({ page }) => {
  await page.goto('/signin');

  await page.getByRole('textbox', { name: 'Username' }).fill('eventum');
  await page.getByRole('textbox', { name: 'Password' }).fill('eventum');
  await page.getByRole('button', { name: 'Sign In' }).click();

  await expect(
    page
      .getByRole('navigation')
      .getByRole('link', { name: 'Projects', exact: true })
  ).toBeVisible();
});

test('signing out closes the studio again', async ({ page }) => {
  await page.goto('/signin');
  await page.getByRole('textbox', { name: 'Username' }).fill('eventum');
  await page.getByRole('textbox', { name: 'Password' }).fill('eventum');
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(
    page
      .getByRole('navigation')
      .getByRole('link', { name: 'Projects', exact: true })
  ).toBeVisible();

  await page.getByRole('button', { name: /Internal user/ }).click();
  await page.getByRole('menuitem', { name: 'Sign out' }).click();

  await expect(page).toHaveURL(/\/signin$/);

  // The session is gone rather than merely navigated away from.
  await page.goto('/projects');
  await expect(page).toHaveURL(/\/signin$/);
});
