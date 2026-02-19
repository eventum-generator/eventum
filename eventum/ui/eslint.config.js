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

export default tseslint.config({
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
});
