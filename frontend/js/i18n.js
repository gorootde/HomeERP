import de from './locales/de.js';
import en from './locales/en.js';

const LOCALES = { de, en };

const _saved = localStorage.getItem('locale');
let _locale = LOCALES[_saved] ?? en;

export function setLocale(lang) {
  _locale = LOCALES[lang] ?? en;
  localStorage.setItem('locale', lang);
}

export function getCurrentLang() {
  return localStorage.getItem('locale') ?? 'en';
}

export function getLocale() {
  return _locale;
}

/**
 * Update all elements with a data-i18n attribute using the current locale.
 * Call this once on startup and whenever the locale changes.
 */
export function applyNavTranslations() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });
}

/**
 * Translate a dot-notation key, optionally interpolating {param} placeholders.
 *
 * @param {string} key    - e.g. 'common.cancel' or 'scanner.err_camera_unavailable'
 * @param {object} params - e.g. { msg: 'Permission denied' }
 * @returns {string}
 */
export function t(key, params = {}) {
  const parts = key.split('.');
  let value = _locale;
  for (const part of parts) {
    if (value == null || typeof value !== 'object') {
      value = undefined;
      break;
    }
    value = value[part];
  }

  if (typeof value !== 'string') {
    // Fall back to the key itself so missing strings are visible during development
    return key;
  }

  // Replace {param} placeholders
  return value.replace(/\{(\w+)\}/g, (_, name) => {
    const replacement = params[name];
    return replacement !== undefined ? String(replacement) : `{${name}}`;
  });
}
