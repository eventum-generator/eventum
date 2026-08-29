import { expect, test } from '@playwright/test';

import {
  createInstance,
  createProject,
  instanceRow,
  openInstanceActions,
} from '../helpers';

/**
 * Monitoring is the live view of the process: what its generators push
 * through the pipeline, and what the host it runs on is occupied with.
 * The resource side is there whatever is running; the pipeline side only
 * appears once something does.
 */
test('the resources of the host are reported', async ({ page }) => {
  await page.goto('/monitoring');

  // The tiles are drawn in capitals by the stylesheet, so the text in
  // the page is the label as it is written in the component.
  for (const tile of ['CPU', 'Memory', 'Disk I/O', 'Network']) {
    await expect(page.getByText(tile, { exact: true })).toBeVisible();
  }

  // Percentages come from the process, so the shape is what is read.
  await expect(page.getByText(/^\d{1,3}%$/).first()).toBeVisible();
});

test('the window of the series is chosen', async ({ page }) => {
  await page.goto('/monitoring');

  // The control hides its radios and draws labels over them, so the
  // label is what a user can click.
  for (const window of ['10 min', '30 min']) {
    await page.getByText(window, { exact: true }).click();
    await expect(page.getByRole('radio', { name: window })).toBeChecked();
  }
});

test('with nothing running it says so and points at the instances', async ({
  page,
}) => {
  await page.goto('/monitoring');

  await expect(page.getByText('No running generators')).toBeVisible();
  await expect(
    page.getByRole('link', { name: 'Go to Instances' })
  ).toHaveAttribute('href', '/instances');
});

test('a running instance appears with what it produces', async ({ page }) => {
  const project = await createProject(page, 'monitor');
  const instance = await createInstance(page, 'monitor', project);

  await openInstanceActions(page, instance);
  await page.getByRole('menuitem', { name: 'Start' }).click();

  const row = await instanceRow(page, instance);
  await expect(row.getByText('Active')).toBeVisible({ timeout: 30_000 });

  await page.goto('/monitoring');

  // The dashboard reads the stats of every running generator, so the
  // one just started has to be named there.
  await expect(page.getByText(instance)).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText('No running generators')).toHaveCount(0);

  await openInstanceActions(page, instance);
  await page.getByRole('menuitem', { name: 'Stop' }).click();
  await expect(row.getByText('Finished')).toBeVisible({ timeout: 30_000 });
});
