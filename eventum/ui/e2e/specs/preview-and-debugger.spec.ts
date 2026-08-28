import { expect, test } from '@playwright/test';

import {
  activePane,
  consolePanel,
  createProject,
  openProject,
  selectStage,
} from '../helpers';

/**
 * The console runs the pipeline against the backend without starting an
 * instance. Both tools take the configuration currently held in the
 * studio, so a preview that returns nothing points either at the
 * request never being sent or at the configuration being sent empty.
 */
test('the timestamps preview returns a distribution', async ({ page }) => {
  const name = await createProject(page, 'preview');

  await openProject(page, name);
  await selectStage(page, 'Input');

  const tool = consolePanel(page);
  await expect(tool.getByText('Console · Timestamps preview')).toBeVisible();

  await tool.getByRole('button', { name: 'Generate' }).click();

  await expect(tool.getByText('Distribution', { exact: true })).toBeVisible();
  await expect(tool.getByText(/[1-9]\d{0,8} total/)).toBeVisible();
  await expect(tool.getByText('Timestamps', { exact: true })).toBeVisible();
});

test('the debugger produces an event', async ({ page }) => {
  const name = await createProject(page, 'debugger');

  await openProject(page, name);
  await selectStage(page, 'Event');

  const tool = consolePanel(page);
  await expect(tool.getByText('Console · Event debugger')).toBeVisible();

  // Producing needs a live plugin instance, and the button stays
  // disabled until the backend confirms one.
  await tool.getByRole('button', { name: 'Start' }).click();
  await expect(tool.getByText('Running', { exact: true })).toBeVisible();

  const produce = tool.getByRole('button', { name: 'Produce' });
  await expect(produce).toBeEnabled();
  await produce.click();

  // The project was created with the default template, whose body is
  // this text - so seeing it is the whole chain reporting back: the
  // config reached the backend, the plugin rendered, the event came out.
  const pane = activePane(page);
  await expect(pane.getByText('Template content')).toBeVisible();
  await expect(
    pane.getByText('No events produced for these parameters.')
  ).toHaveCount(0);

  await tool.getByRole('button', { name: 'Stop' }).click();
  await expect(tool.getByText('Stopped', { exact: true })).toBeVisible();
});
