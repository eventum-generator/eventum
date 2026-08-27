import { expect, test } from '@playwright/test';

/**
 * Every page of the studio is code-split and loaded on demand, so a page
 * can be broken without anything else noticing until someone opens it.
 * The suite therefore opens all of them, from the navigation the user
 * has, and reads the heading each one draws for itself.
 */
const PAGES = [
  ['Monitoring', '/monitoring'],
  ['Projects', '/projects'],
  ['Instances', '/instances'],
  ['Scenarios', '/scenarios'],
  ['Repositories', '/repositories'],
  ['Secrets', '/secrets'],
  ['Settings', '/settings'],
  ['Management', '/management'],
] as const;

test('the navigation reaches every page', async ({ page }) => {
  await page.goto('/');

  // A name is not unique in the navigation - a collapsible group and one
  // of the entries under it can carry the same one - so an entry is
  // addressed by where it leads.
  const nav = page.getByRole('navigation');

  for (const [label, path] of PAGES) {
    await nav.locator(`a[href="${path}"]`).click();

    await expect(page).toHaveURL(new RegExp(`${path}$`));
    await expect(page.getByRole('heading', { name: label })).toBeVisible();
  }

  // Home has no heading of its own - the brand in the header is the
  // one it shows - so it is read by the rails it is made of.
  await nav.locator('a[href="/"]').first().click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByText('RECENT PROJECTS')).toBeVisible();
  await expect(page.getByText('EXPLORE')).toBeVisible();
});

test('an address that is no page of the studio says so', async ({ page }) => {
  await page.goto('/no-such-page');

  await expect(page.getByRole('link', { name: 'Go Back' })).toBeVisible();

  await page.getByRole('link', { name: 'Go Back' }).click();
  await expect(page).toHaveURL(/\/$/);
});

test('the colour scheme is switched and kept', async ({ page }) => {
  await page.goto('/');

  const toggle = page.getByRole('button', {
    name: /Switch to (light|dark) mode/,
  });
  const before = await toggle.getAttribute('aria-label');

  await toggle.click();

  // The label names the scheme it would switch to, so it flips with the
  // scheme itself.
  await expect(toggle).not.toHaveAttribute('aria-label', before ?? '');

  // The choice is stored, so a reload must not fall back to the default.
  await page.reload();
  await expect(
    page.getByRole('button', { name: /Switch to (light|dark) mode/ })
  ).not.toHaveAttribute('aria-label', before ?? '');
});
