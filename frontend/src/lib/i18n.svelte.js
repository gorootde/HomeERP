import de from './i18n/de.js';
import en from './i18n/en.js';

const locales = { de, en };

function loadLang() {
  if (typeof localStorage !== 'undefined') {
    return localStorage.getItem('lang') || 'de';
  }
  return 'de';
}

// Rune-based module state (not a Svelte store): any reactive computation that
// reads `currentLocale` — including indirectly, from inside a plain function
// like `t()` below — gets tracked as depending on it. That's what fixes the
// reactivity bug the old store-based `t()` had: `get(store)` only ever read a
// one-off snapshot, so components calling `t(...)` in their markup never
// re-rendered when the language was switched. See CLAUDE.md / the
// refactoring plan, section 2.
let currentLocale = $state(loadLang());

export function getLocale() {
  return currentLocale;
}

export function setLocale(lang) {
  currentLocale = lang;
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('lang', lang);
  }
}

export function t(key, params = {}) {
  const dict = locales[currentLocale] || locales.de;
  const parts = key.split('.');
  let val = dict;
  for (const p of parts) {
    if (val == null) return key;
    val = val[p];
  }
  if (val == null) return key;
  let str = String(val);
  for (const [k, v] of Object.entries(params)) {
    str = str.replaceAll(`{${k}}`, v);
  }
  return str;
}
