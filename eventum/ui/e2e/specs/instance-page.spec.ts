import { expect, test } from '@playwright/test';

import { createInstance, createProject } from '../helpers';

/**
 * The page of one instance holds everything about it: what it is, what
 * it occupies while it runs, the settings it runs under, and its log.
 * An instance that has never run is the state most of it has to answer
 * for, so that is where these start.
 */
test('the overview says what the instance is', async ({ page }) => {
  const project = await createProject(page, 'inst-page');
  const instance = await createInstance(page, 'inst-page', project);

  await page.goto(`/instances/${instance}`);

  await expect(page.getByRole('heading', { name: instance })).toBeVisible();
  await expect(page.getByText('Idle')).toBeVisible();

  // The project is read off the path the instance was registered with,
  // and it is a link to the project it names.
  await expect(page.getByRole('link', { name: project })).toHaveAttribute(
    'href',
    `/projects/${project}`
  );

  await expect(page.getByText('Live')).toBeVisible();
  await expect(page.getByText('Never')).toBeVisible();
  await expect(
    page.getByText('Instance is not running', { exact: false })
  ).toBeVisible();
});

test('the settings tab shows what the instance runs under', async ({
  page,
}) => {
  const project = await createProject(page, 'inst-settings');
  const instance = await createInstance(page, 'inst-settings', project);

  await page.goto(`/instances/${instance}`);
  await page.getByRole('tab', { name: 'Settings' }).click();

  await expect(page.getByText('Emission mode')).toBeVisible();
  await expect(page.getByRole('radio', { name: 'Live' })).toBeChecked();

  // Generation defaults are the instance's own copy of the application
  // settings, so the section is there with the batching it inherits.
  await expect(page.getByText('Batching mode')).toBeVisible();
});

test('a changed setting is saved and read back', async ({ page }) => {
  const project = await createProject(page, 'inst-save');
  const instance = await createInstance(page, 'inst-save', project);

  await page.goto(`/instances/${instance}`);
  await page.getByRole('tab', { name: 'Settings' }).click();

  // The switch hides its input under the track it draws, so the toggle
  // goes through the keyboard - which is the other way a user has.
  const autostart = page.getByRole('switch', { name: 'Autostart' });
  await autostart.focus();
  await autostart.press('Space');

  await page.getByRole('button', { name: 'Save' }).click();

  await expect(page.getByText('Instance is saved')).toBeVisible();

  // The startup file is what holds this, so a reload is what proves it
  // was written rather than only shown.
  await page.reload();
  await page.getByRole('tab', { name: 'Settings' }).click();
  await expect(page.getByRole('switch', { name: 'Autostart' })).toBeChecked();

  await page.getByRole('tab', { name: 'Overview' }).click();
  await expect(page.getByText('On', { exact: true })).toBeVisible();
});

test('the log tab opens the stream of this instance', async ({ page }) => {
  const project = await createProject(page, 'inst-logs');
  const instance = await createInstance(page, 'inst-logs', project);

  await page.goto(`/instances/${instance}`);
  await page.getByRole('tab', { name: 'Logs' }).click();

  // An instance that never ran has no log file yet, so the viewer is
  // what has to be there - it reports the stream it could not open
  // rather than showing nothing at all.
  await expect(
    page.getByRole('button', { name: 'Go to bottom' })
  ).toBeVisible();
  await expect(page.getByText(/Socket|No logs|waiting/i).first()).toBeVisible();
});

test('an instance is renamed from its own page', async ({ page }) => {
  const project = await createProject(page, 'inst-rename');
  const instance = await createInstance(page, 'inst-rename', project);
  const renamed = `${instance}-renamed`;

  // Renaming is offered from the table rather than from the page of the
  // instance, so this is the path a user actually has.
  await page.goto('/instances');
  await page.getByPlaceholder('search by instance...').fill(instance);
  await page
    .getByRole('row')
    .filter({ hasText: instance })
    .getByRole('button', { name: 'Instance actions' })
    .click();
  await page.getByRole('menuitem', { name: 'Rename' }).click();

  const dialog = page.getByRole('dialog');
  await dialog.getByRole('textbox', { name: /name/i }).fill(renamed);
  await dialog.getByRole('button', { name: /Rename/ }).click();

  await page.goto(`/instances/${renamed}`);
  await expect(page.getByRole('heading', { name: renamed })).toBeVisible();
});

test('an instance is cloned with the project it points at', async ({
  page,
}) => {
  const project = await createProject(page, 'inst-clone');
  const instance = await createInstance(page, 'inst-clone', project);

  await page.goto('/instances');
  await page.getByPlaceholder('search by instance...').fill(instance);
  await page
    .getByRole('row')
    .filter({ hasText: instance })
    .getByRole('button', { name: 'Instance actions' })
    .click();
  await page.getByRole('menuitem', { name: 'Clone' }).click();

  const dialog = page.getByRole('dialog');
  const clone = `${instance}-clone`;

  // The modal proposes a name of its own, so the field is replaced
  // rather than typed into.
  await dialog.getByRole('textbox', { name: 'New instance name' }).fill(clone);
  await dialog.getByRole('button', { name: 'Clone' }).click();

  await expect(page.getByText('Instance is cloned')).toBeVisible();

  // The clone points at the same project, which is what makes it a
  // clone rather than a new instance.
  await page.goto(`/instances/${clone}`);
  await expect(page.getByRole('link', { name: project })).toBeVisible();
});
