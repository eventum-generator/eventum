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
    },
  })
);
