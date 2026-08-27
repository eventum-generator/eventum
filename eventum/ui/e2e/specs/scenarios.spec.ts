import { expect, test } from '@playwright/test';

import {
  confirmDialog,
  createInstance,
  createProject,
  uniqueName,
} from '../helpers';

/**
 * A scenario is a set of instances started and stopped together. It
 * holds no configuration of its own beyond that membership, so what is
 * checked here is that the membership is stored, that the page acts on
 * the set rather than on one instance, and that removing the scenario
 * leaves its instances alone.
 */
async function createScenario(
  page: import('@playwright/test').Page,
  label: string,
  instanceId: string
): Promise<string> {
  const name = uniqueName(label);

  await page.goto('/scenarios');
  await page
    .getByRole('button', { name: /^Create new( scenario)?$/ })
    .first()
    .click();

  await page.getByPlaceholder('e.g. network-monitoring').fill(name);
  await page.getByPlaceholder('Select instances').fill(instanceId);
  await page.getByRole('option', { name: instanceId, exact: true }).click();

  // The list stays open for a second pick and covers the button below
  // it, so it is dismissed before the form is submitted.
  await page.keyboard.press('Escape');

  await page.getByRole('button', { name: 'Create', exact: true }).click();
  await expect(page.getByText(/created/i).first()).toBeVisible();

  return name;
}

test('a scenario is created over an instance and opens on it', async ({
  page,
}) => {
  const project = await createProject(page, 'scen');
  const instance = await createInstance(page, 'scen', project);
  const scenario = await createScenario(page, 'scen', instance);

  await page.goto('/scenarios');
  await page.getByPlaceholder('search by name...').fill(scenario);

  const row = page.getByRole('row').filter({ hasText: scenario });
  await expect(row).toHaveCount(1);

  await row.getByRole('button', { name: 'Scenario actions' }).click();
  await page.getByRole('menuitem', { name: 'Edit' }).click();

  await expect(page.getByRole('heading', { name: scenario })).toBeVisible();
  await expect(page.getByText(instance)).toBeVisible();

  // The set is what the page acts on, and one idle instance can be
  // started but not stopped.
  await expect(page.getByRole('button', { name: 'Start all' })).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Stop all' })).toBeDisabled();
});

test('an instance joins a scenario from its own page', async ({ page }) => {
  const project = await createProject(page, 'scen-join');
  const first = await createInstance(page, 'scen-join', project);
  const scenario = await createScenario(page, 'scen-join', first);

  const second = await createInstance(page, 'scen-joiner', project);

  await page.goto(`/instances/${second}`);
  await expect(page.getByText('Not part of any scenario.')).toBeVisible();

  // The button lists the scenarios this instance is not in yet, so
  // joining one is a pick rather than a form.
  await page.getByRole('button', { name: 'Add to scenario' }).click();
  await page.getByRole('menuitem', { name: scenario }).click();

  await expect(page.getByRole('link', { name: scenario })).toBeVisible();

  await page.goto(`/scenarios/${scenario}`);
  await expect(page.getByText(second)).toBeVisible();
});

test('a scenario is deleted and its instances stay', async ({ page }) => {
  const project = await createProject(page, 'scen-del');
  const instance = await createInstance(page, 'scen-del', project);
  const scenario = await createScenario(page, 'scen-del', instance);

  await page.goto('/scenarios');
  await page.getByPlaceholder('search by name...').fill(scenario);
  await page
    .getByRole('row')
    .filter({ hasText: scenario })
    .getByRole('button', { name: 'Scenario actions' })
    .click();
  await page.getByRole('menuitem', { name: 'Delete' }).click();
  await confirmDialog(page, 'Delete');

  await expect(page.getByRole('row').filter({ hasText: scenario })).toHaveCount(
    0
  );

  // The scenario grouped the instance, it did not own it.
  await page.goto(`/instances/${instance}`);
  await expect(page.getByRole('heading', { name: instance })).toBeVisible();
});
