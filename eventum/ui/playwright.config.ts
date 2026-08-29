import { defineConfig, devices } from '@playwright/test';

const host = process.env.E2E_HOST ?? '127.0.0.1';
// Well clear of the port an Eventum instance is normally reached on:
// the suite refuses to run when something already answers here, so a
// dev instance on the usual port must not be one of them.
const port = process.env.E2E_PORT ?? '19474';

const baseURL = `http://${host}:${port}`;

export const STORAGE_STATE = 'e2e/.tmp/auth/state.json';

export default defineConfig({
  testDir: './e2e',
  outputDir: './e2e/.tmp/results',
  // One backend serves every spec, and it keeps the projects and the
  // instances the specs create. Running them at once would let one
  // spec's list assertions see another spec's resources.
  workers: 1,
  fullyParallel: false,
  // A spec that only passes on a retry is reporting a race, and the
  // suite is meant to surface those rather than paper over them.
  retries: 0,
  // The browser drives a real backend that starts generators and runs
  // previews, so a step is slower than against a mock.
  timeout: 90_000,
  expect: { timeout: 15_000 },
  // A test left focused or marked as expected-to-fail passes locally
  // and silently narrows the suite in CI.
  forbidOnly: !!process.env.CI,
  reporter: process.env.CI
    ? [['html', { outputFolder: 'e2e-report', open: 'never' }], ['github']]
    : [['html', { outputFolder: 'e2e-report', open: 'never' }], ['list']],
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
  },
  projects: [
    {
      name: 'setup',
      testMatch: '**/auth.setup.ts',
    },
    {
      name: 'chromium',
      testMatch: '**/*.spec.ts',
      dependencies: ['setup'],
      use: {
        ...devices['Desktop Chrome'],
        // The studio lays panels out side by side above this width and
        // collapses to a switcher below it, so the viewport decides
        // which of the two layouts the specs meet.
        viewport: { width: 1600, height: 1000 },
        storageState: STORAGE_STATE,
      },
    },
  ],
  webServer: {
    command: 'node e2e/backend/serve.mjs',
    url: `${baseURL}/api/openapi.json`,
    // Never reuse a backend that is already answering. The specs write
    // projects, overwrite a generator.yml and delete an instance, so
    // meeting an instance with real data on this port would mutate it.
    // A port held by something else fails the run instead, which is the
    // outcome that can be diagnosed.
    reuseExistingServer: false,
    timeout: 180_000,
    stdout: 'pipe',
    stderr: 'pipe',
  },
});
