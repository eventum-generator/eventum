import eslint from '@eslint/js';
import tsParser from '@typescript-eslint/parser';
import eslintConfigPrettierFlat from 'eslint-config-prettier/flat';
import importPlugin from 'eslint-plugin-import';
import jsxA11y from 'eslint-plugin-jsx-a11y';
import reactPlugin from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import sonarjs from 'eslint-plugin-sonarjs';
import storybook from 'eslint-plugin-storybook';
import eslintPluginUnicorn from 'eslint-plugin-unicorn';
import globals from 'globals';
import tseslint from 'typescript-eslint';

export default tseslint.config({
  // Build output, not source - never lint it.
  ignores: ['storybook-static/**'],
}, {
  files: ['**/*.{ts,tsx}'],
  extends: [
    eslint.configs.recommended,
    tseslint.configs.recommendedTypeChecked,
    tseslint.configs.stylisticTypeChecked,
    eslintConfigPrettierFlat,
    reactPlugin.configs.flat.recommended,
    reactPlugin.configs.flat['jsx-runtime'],
    reactHooks.configs['recommended-latest'],
    reactRefresh.configs.recommended,
    importPlugin.flatConfigs.recommended,
    jsxA11y.flatConfigs.recommended,
    eslintPluginUnicorn.configs.recommended,
    sonarjs.configs.recommended,
  ],
  rules: {
    'unicorn/filename-case': 'off',
    'unicorn/prevent-abbreviations': 'off',
    'unicorn/no-null': 'off',
    'sonarjs/void-use': 'off',
    'unicorn/prefer-ternary': 'off',
    'unicorn/no-nested-ternary': 'off',
    'sonarjs/no-nested-conditional': 'off',
    'unicorn/no-negated-condition': 'off',
    'unicorn/prefer-switch': 'off',
    'sonarjs/no-useless-intersection': 'off',
    'sonarjs/no-nested-functions': 'off',
    'no-restricted-syntax': [
      'error',
      {
        selector: "Literal[value=/^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/]",
        message: 'Hardcoded hex colour - use a var(--ev-*) token or theme value.',
      },
      {
        selector: "Literal[value=/^(?:rgba?|hsla?)\\(/]",
        message: 'Hardcoded colour function - use a var(--ev-*) token or theme value.',
      },
    ],
  },
  languageOptions: {
    ecmaVersion: 2020,
    globals: globals.browser,
    parser: tsParser,
    parserOptions: {
      ecmaFeatures: {
        jsx: true,
      },
      projectService: true,
      tsconfigRootDir: import.meta.dirname,
    },
  },
  settings: {
    'import/resolver': {
      typescript: true,
      node: {
        extensions: ['.ts', '.tsx'],
      },
    },
    react: {
      version: 'detect',
    },
  },
},
// Spread as its own top-level entries (not nested in `extends`) so each
// sub-config keeps its native `files` glob - one set of rules for
// `**/*.stories.*`, another narrower set for `.storybook/main.*`. Folding
// this into a single files-scoped override would override (not
// intersect) those globs and misapply story-only rules to main.ts.
...storybook.configs['flat/recommended'],
{
  files: ['**/*.stories.tsx', '.storybook/**'],
  rules: {
    // Story modules and Storybook config files export plain objects
    // (meta/preview/config), not components - the fast-refresh export
    // shape rule does not apply here.
    'react-refresh/only-export-components': 'off',
  },
});
