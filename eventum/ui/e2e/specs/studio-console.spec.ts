import { expect, test } from '@playwright/test';

import {
  activePane,
  consolePanel,
  createProject,
  inspector,
  selectStage,
} from '../helpers';

/**
 * The console is where a configuration is tried out before it is saved.
 * Its three tools stay mounted so each keeps what it holds while the
 * user moves between stages, and the panel itself can be folded away or
 * given the whole window - so what is checked is that the tool of the
 * stage in view is the one that answers.
 */
test('the console follows the stage in view', async ({ page }) => {
  const project = await createProject(page, 'console');

  await page.goto(`/projects/${project}`);

  await expect(page.getByText('CONSOLE · TIMESTAMPS PREVIEW')).toBeVisible();

  await selectStage(page, 'Event');
  await expect(page.getByText('CONSOLE · EVENT DEBUGGER')).toBeVisible();

  await selectStage(page, 'Output');
  await expect(page.getByText('CONSOLE · FORMATTER PREVIEW')).toBeVisible();
});

test('the console folds away and comes back', async ({ page }) => {
  const project = await createProject(page, 'console-fold');

  await page.goto(`/projects/${project}`);

  const collapse = page.getByRole('button', { name: 'Collapse console' });
  await collapse.click();

  // Folded away, it offers nothing but coming back - there is no room
  // for the tool or for maximising it.
  await expect(
    page.getByRole('button', { name: 'Maximize console' })
  ).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Generate' })).toBeHidden();

  await collapse.click();
  await expect(page.getByRole('button', { name: 'Generate' })).toBeVisible();
});

test('the console takes the whole window and gives it back', async ({
  page,
}) => {
  const project = await createProject(page, 'console-max');

  await page.goto(`/projects/${project}`);

  await page.getByRole('button', { name: 'Maximize console' }).click();

  // With the console over everything, the panels behind it are hidden
  // rather than merely covered - they keep what they hold.
  await expect(inspector(page)).toBeHidden();

  await page.getByRole('button', { name: 'Maximize console' }).click();
  await expect(inspector(page)).toBeVisible();
});

test('the state of a template is read once the debugger runs', async ({
  page,
}) => {
  const project = await createProject(page, 'console-state');

  await page.goto(`/projects/${project}`);
  await selectStage(page, 'Event');

  const console_ = consolePanel(page);

  // The state endpoints answer for a live plugin instance, so the view
  // is offered but cannot be entered before one exists.
  await expect(console_.getByText('State', { exact: true })).toBeVisible();
  await expect(page.getByRole('radio', { name: 'State' })).toBeDisabled();

  await console_.getByRole('button', { name: 'Start' }).click();
  await expect(console_.getByText('Running', { exact: true })).toBeVisible();

  await console_.getByText('State', { exact: true }).click();
  await expect(page.getByText('CONSOLE · TEMPLATE STATE')).toBeVisible();

  // Every scope a template writes into is there, each under a heading
  // of its own, and the local one asks which template it belongs to.
  await expect(
    activePane(page).getByRole('heading', { name: 'Shared state' })
  ).toBeVisible();
  await expect(
    activePane(page).getByRole('heading', { name: 'Global state' })
  ).toBeVisible();
  await expect(
    activePane(page).getByText('Select a template to inspect its local state.')
  ).toBeVisible();

  // The debugger keeps the plugin instance open, and it is that view
  // which releases it - one backend serves every spec.
  await console_.getByText('Debugger', { exact: true }).click();
  await console_.getByRole('button', { name: 'Stop' }).click();
  await expect(console_.getByText('Stopped', { exact: true })).toBeVisible();
});
