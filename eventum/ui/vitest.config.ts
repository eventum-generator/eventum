import { mergeConfig } from 'vite';
import { defineConfig } from 'vitest/config';

import viteConfig from './vite.config';

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      include: ['src/**/*.test.{ts,tsx}'],
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      restoreMocks: true,
      coverage: {
        provider: 'v8',
        reporter: ['text-summary', 'html', 'json', 'lcov'],
        reportsDirectory: 'coverage',
        include: ['src/**/*.{ts,tsx}'],
        exclude: [
          // Test scaffolding and the specs themselves.
          'src/**/*.test.{ts,tsx}',
          'src/test/**',
          // Ambient declarations carry no statements.
          'src/**/*.d.ts',
          // The entry point mounts the app into a real document.
          'src/main.tsx',
        ],
        // A ratchet, not a target: it sits just under what the suite
        // covers today, so a change that drops coverage fails. Raise it
        // as coverage grows; never lower it to make a red run green.
        thresholds: {
          statements: 72,
          branches: 60,
          functions: 67,
          lines: 82,
        },
      },
    },
  })
);
