import { expect, test } from '@playwright/test';

/**
 * The management page reports what this process is and offers the two
 * actions that end it. Both are confirmed first, and this suite runs
 * against the very instance they would take down - so what is checked
 * here is that the confirmation stands between the click and the act.
 */
test('the page reports the running instance', async ({ page }) => {
  await page.goto('/management');

  await expect(page.getByText('Running', { exact: true })).toBeVisible();

  // The figures come from the process itself, so they are read as
  // shapes rather than as fixed values.
  await expect(page.getByText(/^\d+\.\d+\.\d+$/).first()).toBeVisible();
  await expect(page.getByText('Hostname')).toBeVisible();
  await expect(page.getByText('Platform')).toBeVisible();
});

test('the log stream is shown and can be navigated', async ({ page }) => {
  await page.goto('/management');

  await expect(
    page.getByRole('button', { name: 'Go to bottom' })
  ).toBeVisible();
  await page.getByRole('button', { name: 'Go to top' }).click();

  // The instance logs its own requests, so the stream is never empty -
  // the line numbers beside it are drawn per line received.
  await expect(page.getByText('1', { exact: true }).first()).toBeVisible();
});

test.describe('the actions that end the instance', () => {
  for (const [action, title] of [
    ['Restart', 'Restarting instance'],
    ['Stop', 'Stopping instance'],
  ] as const) {
    test(`${action} asks first and does nothing when cancelled`, async ({
      page,
    }) => {
      await page.goto('/management');

      await page.getByRole('button', { name: action, exact: true }).click();

      const dialog = page.getByRole('dialog');
      await expect(dialog.getByText(title)).toBeVisible();

      await dialog.getByRole('button', { name: 'Cancel' }).click();
      await expect(dialog).toHaveCount(0);

      // Cancelling leaves the instance where it was, which the page
      // keeps reporting because it keeps polling it.
      await expect(page.getByText('Running', { exact: true })).toBeVisible();
    });
  }
});
