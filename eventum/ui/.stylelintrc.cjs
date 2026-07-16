module.exports = {
  plugins: ['stylelint-declaration-strict-value'],
  rules: {
    'color-no-hex': true,
    'declaration-block-no-duplicate-properties': true,
    'no-duplicate-selectors': true,
    'scale-unlimited/declaration-strict-value': [
      ['/color$/', 'fill', 'stroke', 'background-color', 'border-color', 'outline-color'],
      {
        ignoreValues: ['transparent', 'currentColor', 'inherit', 'none', 'unset', 'initial'],
        disableFix: true,
        severity: 'warning',
      },
    ],
  },
  overrides: [
    {
      files: ['src/theme/tokens.css'],
      rules: { 'color-no-hex': null, 'scale-unlimited/declaration-strict-value': null },
    },
  ],
};
