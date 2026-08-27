import { Locator, Page, expect } from '@playwright/test';

/**
 * A name no other run can collide with.
 *
 * The backend keeps what a spec creates, and locally the suite reuses a
 * backend that is already up, so a fixed name would fail the second run
 * with a conflict.
 */
export function uniqueName(label: string): string {
  return `e2e-${label}-${Date.now().toString(36)}`;
}

/** Create a project of the given event plugin type and return its name. */
export async function createProject(
  page: Page,
  label: string,
  projectType = 'Template'
): Promise<string> {
  const name = uniqueName(label);

  await page.goto('/projects');

  // The page draws an empty state until the first project exists and a
  // toolbar afterwards, and the two spell the action differently.
  await page
    .getByRole('button', { name: /^Create new( project)?$/ })
    .first()
    .click();

  // Picking a project type opens a second modal over the first, so the
  // type button is matched by its leading name - the whole accessible
  // name carries the description of the plugin too.
  await page
    .getByRole('button', { name: new RegExp(`^${projectType}\\b`) })
    .click();

  await page.getByRole('textbox', { name: 'Project name' }).fill(name);
  await page.getByRole('button', { name: 'Create', exact: true }).click();

  await expect(page.getByText('Project is created')).toBeVisible();

  return name;
}

/** Open the studio of a project by name. */
export async function openProject(page: Page, name: string): Promise<void> {
  await page.goto(`/projects/${name}`);
  await expect(page.getByRole('heading', { name, exact: true })).toBeVisible();
}

/** Register an instance over a project and return the instance name. */
export async function createInstance(
  page: Page,
  label: string,
  projectName: string
): Promise<string> {
  const id = uniqueName(label);

  await page.goto('/instances');

  await page
    .getByRole('button', { name: /^Create( new)?( instance)?$/ })
    .first()
    .click();

  await page.getByRole('textbox', { name: 'Instance name' }).fill(id);

  // The project is picked from a searchable select, which only offers an
  // option once its input narrows the list.
  await page.getByRole('textbox', { name: 'Project name' }).fill(projectName);
  await page.getByRole('option', { name: projectName, exact: true }).click();

  await page.getByRole('button', { name: 'Create', exact: true }).click();

  await expect(page.getByText('Instance is created')).toBeVisible();

  return id;
}

/**
 * The row of a project, found through the search field.
 *
 * The table pages at fifteen rows and the suite adds to the workspace
 * as it runs, so by the last spec a row created a moment ago may sit on
 * a page that is not shown. Narrowing first is what keeps the row
 * reachable no matter how much came before it.
 */
export async function projectRow(page: Page, name: string): Promise<Locator> {
  await page.goto('/projects');
  await page.getByPlaceholder('search by name...').fill(name);

  const row = page.getByRole('row').filter({ hasText: name });
  await expect(row).toHaveCount(1);

  return row;
}

/** The row of an instance, found through the search field. */
export async function instanceRow(page: Page, id: string): Promise<Locator> {
  await page.goto('/instances');
  await page.getByPlaceholder('search by instance...').fill(id);

  const row = page.getByRole('row').filter({ hasText: id });
  await expect(row).toHaveCount(1);

  return row;
}

/** Open the actions menu of an instance row. */
export async function openInstanceActions(
  page: Page,
  instanceId: string
): Promise<void> {
  const row = await instanceRow(page, instanceId);
  await row.getByRole('button', { name: 'Instance actions' }).click();
}

/** Open the actions menu of a project row. */
export async function openProjectActions(
  page: Page,
  projectName: string
): Promise<void> {
  const row = await projectRow(page, projectName);
  await row.getByRole('button', { name: 'Project actions' }).click();
}

/**
 * Confirm a dialog raised by a destructive action.
 *
 * Every one of them is the same confirm modal, and its buttons carry
 * the verb of the action rather than a generic "OK".
 */
export async function confirmDialog(page: Page, label: string): Promise<void> {
  await page
    .getByRole('dialog')
    .getByRole('button', { name: label, exact: true })
    .click();
}

/** Switch the studio to a pipeline stage. */
export async function selectStage(
  page: Page,
  stage: 'Input' | 'Event' | 'Output'
): Promise<void> {
  await page.getByRole('button', { name: `${stage} stage` }).click();
}

/**
 * The inspector panel, where the configuration of the selected plugin
 * is edited.
 *
 * Scoping matters: the console below it runs the same pipeline stage
 * and labels its own fields the same way, so an unscoped "Count" or
 * "Start" matches in both panels.
 */
export function inspector(page: Page): Locator {
  return page.locator('.studio-inspector');
}

/** The console panel, where the previews and the debugger run. */
export function consolePanel(page: Page): Locator {
  return page.locator('.studio-console');
}

/**
 * The console pane of the stage currently selected.
 *
 * Every stage tool stays mounted so it keeps its state, so the console
 * holds three panes at once and only one of them is shown.
 */
export function activePane(page: Page): Locator {
  return consolePanel(page).locator('.stage-pane[data-active="true"]');
}
