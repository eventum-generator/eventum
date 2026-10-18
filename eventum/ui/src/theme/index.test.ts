import { DEFAULT_THEME, mergeMantineTheme } from '@mantine/core';
import { describe, expect, it } from 'vitest';

import { cssVariablesResolver, theme } from './index';

/**
 * A live status indicator reads its halo from a variable per colour, and
 * a variable the resolver does not define leaves that indicator unlit.
 */
describe('cssVariablesResolver', () => {
  const resolved = cssVariablesResolver(
    mergeMantineTheme(DEFAULT_THEME, theme)
  );

  it.each(['green', 'yellow', 'red'])(
    'defines the %s halo in both schemes',
    (color) => {
      expect(resolved.light).toHaveProperty(`--ev-glow-${color}`);
      expect(resolved.dark).toHaveProperty(`--ev-glow-${color}`);
    }
  );
});
