import { Locator, expect, test } from '@playwright/test';

import {
  confirmDialog,
  createInstance,
  createProject,
  instanceRow,
  openInstanceActions,
} from '../helpers';

/**
 * The figure a metrics card holds, by the name of the reading.
 *
 * The cards are the only part of the panel that carries a measurement -
 * the title of the dialog is drawn by whoever opened it, so it says
 * nothing about whether the instance was measured at all. The figures
 * name themselves, so the pipeline graph in the same panel - which
 * labels its nodes with the same words - cannot be read instead.
 */
function metric(panel: Locator, label: string): Locator {
  return panel.locator(`[data-metric="${label}"]`);
}

/**
 * An instance is registered over a project, started, reports what it
 * produces, and stops. Every step is a separate backend call whose
 * result the table only reflects after a refetch, so a status that
 * never leaves "Starting" is as much a failure as one that never
 * starts.
 */
test('an instance starts, reports and stops', async ({ page }) => {
  const projectName = await createProject(page, 'lifecycle');
  const instanceId = await createInstance(page, 'lifecycle', projectName);

  const row = await instanceRow(page, instanceId);
  await expect(row.getByText('Idle')).toBeVisible();

  await openInstanceActions(page, instanceId);
  await page.getByRole('menuitem', { name: 'Start' }).click();

  await expect(row.getByText('Active')).toBeVisible({ timeout: 30_000 });

  await openInstanceActions(page, instanceId);
  await page.getByRole('menuitem', { name: 'Show metrics' }).click();

  // Stats are served only for a running instance: the panel reports
  // them, or it reports that the instance has stopped. Reading the
  // figures is what tells the two apart.
  // Both figures exist only in the branch that received stats, so
  // reading them at all is what rules out the stopped state - their
  // value may legitimately still be zero at this instant.
  const metrics = page.getByRole('dialog');
  await expect(metrics.getByText('Instance is not running')).toHaveCount(0);
  await expect(metric(metrics, 'Written')).toHaveText(/^\d+$/);
  await expect(metric(metrics, 'Input EPS')).toHaveText(/^\d+\.\d\d$/);

  // The panel re-reads the stats every few seconds, so a counter that
  // stays at zero means the instance is up without producing anything.
  // The first timestamp of the default project arrives after 5s.
  await expect(metric(metrics, 'Generated')).toHaveText(/^[1-9]\d*$/, {
    timeout: 30_000,
  });

  await page.keyboard.press('Escape');
  await expect(metrics).toHaveCount(0);

  await openInstanceActions(page, instanceId);
  await page.getByRole('menuitem', { name: 'Stop' }).click();

  // A stopped instance ends up in a terminal state. "Failed" is one the
  // backend reports for a run that ended badly, so it is not accepted
  // here - stopping a healthy instance must not produce it.
  await expect(row.getByText('Finished')).toBeVisible({ timeout: 30_000 });
});

test('an instance can be deleted', async ({ page }) => {
  const projectName = await createProject(page, 'delete-inst');
  const instanceId = await createInstance(page, 'delete-inst', projectName);

  await openInstanceActions(page, instanceId);
  await page.getByRole('menuitem', { name: 'Delete' }).click();

  await confirmDialog(page, 'Delete');

  await expect(
    page.getByRole('row').filter({ hasText: instanceId })
  ).toHaveCount(0);
});
