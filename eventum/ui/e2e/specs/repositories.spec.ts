import { Page, expect, test } from '@playwright/test';

/**
 * A connected repository is fetched from wherever it is published, so
 * the pages that list one talk to a host outside this machine. These
 * checks answer the repository requests from the browser instead: what
 * is under test is the studio, and a suite that reaches GitHub would
 * report its rate limit as a defect of this page.
 */
const CONNECTED = [
  {
    name: 'content-packs',
    url: 'https://github.com/eventum-generator/content-packs.git',
    ref: 'master',
    status: {
      state: 'available',
      checked_at: '2026-08-01T10:00:00+00:00',
      reason: null,
    },
  },
];

const CATALOG = {
  revision: 'a1b2c3d4',
  refreshed_at: '2026-08-01T10:00:00+00:00',
  committed_at: '2026-07-31T09:00:00+00:00',
  author: 'Eventum Team',
  entries: [
    {
      name: 'web-nginx',
      path: 'generators/web-nginx',
      title: 'Nginx access log',
      summary: 'Access and error events of an nginx server',
      file_count: 7,
      size: 20_480,
      installed_as: [],
    },
  ],
};

const DISCOVERY = {
  topic: 'eventum-generators',
  query: 'topic:eventum-generators',
  entries: [
    {
      name: 'content-packs',
      full_name: 'eventum-generator/content-packs',
      url: 'https://github.com/eventum-generator/content-packs.git',
      page_url: 'https://github.com/eventum-generator/content-packs',
      owner: 'eventum-generator',
      description: 'Official repository of generators for Eventum',
      topics: ['eventum-generators'],
      stars: 5,
      updated_at: '2026-07-31T09:00:00+00:00',
      license: 'Apache-2.0',
      archived: false,
      official: true,
      connected: false,
    },
  ],
  total_count: 1,
  refreshed_at: '2026-08-01T10:00:00+00:00',
  rate: { remaining: 9, reset_at: '2026-08-01T11:00:00+00:00' },
};

/** Answer every repository request with what the flow needs. */
async function stubRepositories(page: Page, connected = CONNECTED) {
  await page.route('**/api/repositories/discover*', (route) =>
    route.fulfill({ json: DISCOVERY })
  );
  await page.route('**/api/repositories/*/catalog', (route) =>
    route.fulfill({ json: CATALOG })
  );
  await page.route('**/api/repositories/', (route) =>
    route.request().method() === 'GET'
      ? route.fulfill({ json: connected })
      : route.fulfill({ status: 204, body: '' })
  );
}

test('with nothing connected the page says what a repository is for', async ({
  page,
}) => {
  await stubRepositories(page, []);

  await page.goto('/repositories');

  await expect(page.getByText('No repositories connected')).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Connect repository' })
  ).toBeVisible();
});

test('a connected repository is listed with its catalog', async ({ page }) => {
  await stubRepositories(page);

  await page.goto('/repositories');

  await expect(page.getByText('1 repository connected')).toBeVisible();
  await expect(page.getByText('content-packs').first()).toBeVisible();
  await expect(page.getByText('Reachable')).toBeVisible();

  // The catalog is read per repository, so it is opened rather than
  // listed alongside.
  await page.getByText('content-packs').first().click();
  await expect(page.getByText('Nginx access log')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Install' })).toBeVisible();
});

test('the discover tab lists what carries the topic', async ({ page }) => {
  await stubRepositories(page, []);

  await page.goto('/repositories');
  await page.getByRole('tab', { name: 'Discover' }).click();

  await expect(page.getByText('1 repository found')).toBeVisible();
  await expect(page.getByText('eventum-generator/content-packs')).toBeVisible();
  await expect(page.getByText('official', { exact: true })).toBeVisible();

  // What is published is not reviewed, and the page has to say so - a
  // generator carries code that runs on this machine.
  await expect(
    page.getByText('Community repositories are not reviewed')
  ).toBeVisible();
});

test('connecting from discover carries the repository over', async ({
  page,
}) => {
  await stubRepositories(page, []);

  await page.goto('/repositories');
  await page.getByRole('tab', { name: 'Discover' }).click();
  await page.getByRole('button', { name: 'Connect', exact: true }).click();

  // The form opens filled from the entry, so the user only confirms.
  const dialog = page.getByRole('dialog');
  await expect(
    dialog.getByRole('textbox', { name: 'Name', exact: true })
  ).toHaveValue('content-packs');
  await expect(dialog.getByRole('textbox', { name: 'URL' })).toHaveValue(
    'https://github.com/eventum-generator/content-packs.git'
  );
});

test('a repository with a name the backend would refuse is stopped here', async ({
  page,
}) => {
  await stubRepositories(page, []);

  await page.goto('/repositories');
  await page.getByRole('button', { name: 'Connect repository' }).click();

  const dialog = page.getByRole('dialog');
  await dialog
    .getByRole('textbox', { name: 'Name', exact: true })
    .fill('not a name');
  await dialog
    .getByRole('textbox', { name: 'URL' })
    .fill('https://example.com/repo.git');

  await expect(dialog.getByRole('button', { name: 'Connect' })).toBeDisabled();
});
