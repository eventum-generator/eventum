import eslint from '@eslint/js';
import tsParser from '@typescript-eslint/parser';
import eslintConfigPrettierFlat from 'eslint-config-prettier/flat';
import importPlugin from 'eslint-plugin-import';
import jsxA11y from 'eslint-plugin-jsx-a11y';
import reactPlugin from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import sonarjs from 'eslint-plugin-sonarjs';
import eslintPluginUnicorn from 'eslint-plugin-unicorn';
import globals from 'globals';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  {
    // Generated output, not sources: the coverage report and the
    // Playwright artifacts both ship bundled scripts.
    ignores: ['coverage/**', 'e2e-report/**', 'e2e/.tmp/**'],
  },
  {
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
          selector:
            'Literal[value=/^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/]',
          message:
            'Hardcoded hex colour - use a Mantine CSS variable or colour prop.',
        },
        {
          selector: 'Literal[value=/^(?:rgba?|hsla?)\\(/]',
          message:
            'Hardcoded colour function - use a Mantine CSS variable or colour prop.',
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
  {
    // Unit tests build fixtures and mocks, which a few rules written for
    // production code read as defects.
    files: ['src/**/*.test.{ts,tsx}', 'src/test/**/*.{ts,tsx}'],
    rules: {
      // Mocking a client method means referencing it unbound.
      // `expect.objectContaining` and its siblings are typed `any`, so
      // every assertion that names part of a call reads as unsafe.
      '@typescript-eslint/no-unsafe-assignment': 'off',
      '@typescript-eslint/unbound-method': 'off',
      // Fixtures carry credentials and plain-http values on purpose -
      // the insecure ones are there to be rejected.
      'sonarjs/no-hardcoded-passwords': 'off',
      'sonarjs/no-clear-text-protocols': 'off',
      // Comparing two key sets, not sorting anything a user reads.
      'sonarjs/no-alphabetical-sort': 'off',
      // A helper belongs next to the tests that share it.
      'unicorn/consistent-function-scoping': 'off',
      'unicorn/no-await-expression-member': 'off',
      // A wrapper defined inline in a test is not a component of the app.
      'react/display-name': 'off',
      'react/prop-types': 'off',
    },
  },
  {
    // The browser tests run in Node and drive the app from the outside,
    // so the browser globals and the React rules do not apply to them.
    files: ['e2e/**/*.ts', 'playwright.config.ts'],
    languageOptions: {
      globals: globals.node,
    },
    rules: {
      'react-refresh/only-export-components': 'off',
      // A spec reads as a sequence of steps; splitting one to satisfy a
      // duplication budget makes it harder to follow.
      'sonarjs/no-duplicate-string': 'off',
    },
  },
  {
    // The script that starts the backend is plain Node, outside the
    // TypeScript project the rules above are type-checked against.
    files: ['e2e/**/*.mjs'],
    extends: [eslint.configs.recommended],
    languageOptions: {
      globals: globals.node,
      sourceType: 'module',
    },
  }
);
