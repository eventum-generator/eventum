/**
 * Runs the Eventum backend the browser tests drive.
 *
 * The backend is the real one, started over a throwaway directory of
 * its own: its own generators directory, startup file, keyring and
 * logs. It serves the built Studio bundle and the API on a single port,
 * so the tests exercise what the package actually ships rather than a
 * dev server proxying to an API.
 *
 * Plain JavaScript on purpose - Playwright starts this through
 * `webServer.command`, a shell command with no TypeScript loader in
 * front of it.
 */
import { spawn } from 'node:child_process';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const uiDir = path.resolve(import.meta.dirname, '../..');
const repoRoot = path.resolve(uiDir, '../..');

// Kept inside the UI package (and gitignored) rather than in the system
// temporary directory: a failed run leaves the generators and the logs
// behind next to the report that refers to them.
const runDir = path.join(uiDir, 'e2e', '.tmp', 'instance');

const host = process.env.E2E_HOST ?? '127.0.0.1';
const port = process.env.E2E_PORT ?? '19474';

/**
 * A path as a YAML scalar. A path is not guaranteed to be free of the
 * characters YAML reads as syntax - a drive letter alone carries a
 * colon - so it travels quoted.
 */
function quote(value) {
  return JSON.stringify(value);
}

/** Lay out a directory the backend can be pointed at. */
function prepareRunDir() {
  // A directory left by an earlier run would carry its projects and
  // instances into this one, and every spec asserting on a list would
  // see them.
  rmSync(runDir, { recursive: true, force: true });
  mkdirSync(path.join(runDir, 'logs'), { recursive: true });
  mkdirSync(path.join(runDir, 'generators'), { recursive: true });

  const startupFile = path.join(runDir, 'startup.yml');
  writeFileSync(startupFile, '[]\n');

  const configFile = path.join(runDir, 'eventum.yml');
  writeFileSync(
    configFile,
    [
      `server.host: "${host}"`,
      `server.port: ${port}`,
      'server.ui.enabled: true',
      'server.api.enabled: true',
      'server.auth.user: eventum',
      'server.auth.password: eventum',
      'generation.timezone: UTC',
      // A small batch flushed twice a second keeps a started instance
      // reporting written events within the span of a test, where the
      // shipped defaults (10000 events, one second) would report none.
      'generation.batch.size: 1',
      'generation.batch.delay: 0.5',
      'log.level: info',
      'log.format: plain',
      `path.logs: ${quote(path.join(runDir, 'logs'))}`,
      `path.startup: ${quote(startupFile)}`,
      `path.generators_dir: ${quote(path.join(runDir, 'generators'))}`,
      `path.keyring_cryptfile: ${quote(path.join(runDir, 'cryptfile.cfg'))}`,
      '',
    ].join('\n')
  );

  return configFile;
}

const configFile = prepareRunDir();

const backend = spawn('uv', ['run', 'eventum', 'run', '-c', configFile], {
  cwd: repoRoot,
  stdio: 'inherit',
});

backend.on('error', (error) => {
  console.error('Failed to start the backend:', error.message);
  process.exit(1);
});

backend.on('exit', (code, signal) => {
  process.exit(code ?? (signal ? 1 : 0));
});

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    backend.kill(signal);
  });
}
