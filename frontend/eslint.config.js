import js from '@eslint/js';
import svelte from 'eslint-plugin-svelte';
import globals from 'globals';

export default [
  js.configs.recommended,
  ...svelte.configs.recommended,
  {
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: {
      // Stylistic/opt-in conventions this project hasn't adopted (typed
      // routing via resolve(), SvelteDate, keyed #each everywhere) — left
      // off for the baseline so linting flags real bugs, not a house style.
      'svelte/require-each-key': 'off',
      'svelte/no-navigation-without-resolve': 'off',
      'svelte/prefer-svelte-reactivity': 'off',
      // `catch {}` is this project's deliberate fail-soft convention
      // (see CLAUDE.md) — don't flag it, but still catch other empty blocks.
      'no-empty': ['error', { allowEmptyCatch: true }],
    },
  },
  {
    ignores: ['build/', '.svelte-kit/', 'dist/', 'e2e-data/', 'playwright-report/', 'test-results/'],
  },
];
