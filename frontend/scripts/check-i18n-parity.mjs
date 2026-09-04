#!/usr/bin/env node
// Fails the build if the DE and EN translation dictionaries drift apart —
// a missing key falls back to the raw key at runtime (see `t()` in
// `src/lib/i18n.svelte.js`), which is easy to miss without this check.
import de from '../src/lib/i18n/de.js';
import en from '../src/lib/i18n/en.js';

function flatten(obj, prefix = '') {
  const keys = [];
  for (const [k, v] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${k}` : k;
    if (v !== null && typeof v === 'object') {
      keys.push(...flatten(v, path));
    } else {
      keys.push(path);
    }
  }
  return keys;
}

const deKeys = new Set(flatten(de));
const enKeys = new Set(flatten(en));

const missingInEn = [...deKeys].filter((k) => !enKeys.has(k)).sort();
const missingInDe = [...enKeys].filter((k) => !deKeys.has(k)).sort();

if (missingInEn.length || missingInDe.length) {
  console.error('i18n key parity check failed:');
  if (missingInEn.length) {
    console.error(`  Missing in en.js (${missingInEn.length}):`);
    for (const k of missingInEn) console.error(`    ${k}`);
  }
  if (missingInDe.length) {
    console.error(`  Missing in de.js (${missingInDe.length}):`);
    for (const k of missingInDe) console.error(`    ${k}`);
  }
  process.exit(1);
}

console.log(`i18n key parity OK (${deKeys.size} keys).`);
