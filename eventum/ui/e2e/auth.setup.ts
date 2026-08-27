import { expect, test as setup } from '@playwright/test';

import { STORAGE_STATE } from '../playwright.config';

/**
 * Sign in once and keep the session for every spec.
 *
 * Every route is guarded and redirects to the sign-in page on an
 * unauthenticated request, so this also covers the sign-in form itself:
 * a broken one fails here instead of failing every spec with a
 * redirect.
 */
setup('sign in', async ({ page }) => {
  await page.goto('/signin');

  await expect(
    page.getByRole('heading', { name: 'Sign in to Eventum' })
  ).toBeVisible();

  await page.getByLabel('Username').fill('eventum');
  await page.getByLabel('Password').fill('eventum');
  await page.getByRole('button', { name: 'Sign In' }).click();

  // The form navigates to the root on success, and the sidebar is the
  // first thing the authenticated shell draws.
  await expect(
    page.getByRole('link', { name: 'Projects', exact: true })
  ).toBeVisible();

  await page.context().storageState({ path: STORAGE_STATE });
});
