/**
 * Pure sort / filter / search helpers behind `DataTable.svelte`. Kept
 * component-free so the ordering and matching rules are unit-testable
 * (`tests/unit/datatable.test.js`).
 *
 * A column def (see DataTable.svelte) may carry:
 *   value(row)     — shared accessor for sorting, `search: true` and shorthand filters
 *   sortValue(row) — optional sort override (defaults to value)
 *   filter         — 'text' | 'select' | { kind, options, placeholder?, match(row, v) }
 */

// One shared collator: German locale, natural number ordering ("Pos 2" < "Pos 10"),
// case/diacritic-insensitive. Instantiating per comparison is measurably slower on
// the ~500-row lists this feeds.
const collator = new Intl.Collator('de', { numeric: true, sensitivity: 'base' });

/** Compare two cell values. Numbers order numerically, everything else via the
 *  collator over its string form. `null` / `undefined` / `''` always sort last,
 *  regardless of direction. Returns 0 for equal keys so `Array#sort` stays stable. */
export function compareValues(a, b, dir = 'asc') {
  const sign = dir === 'desc' ? -1 : 1;
  const aEmpty = a == null || a === '';
  const bEmpty = b == null || b === '';
  if (aEmpty && bEmpty) return 0;
  if (aEmpty) return 1;
  if (bEmpty) return -1;
  const base = typeof a === 'number' && typeof b === 'number'
    ? (a < b ? -1 : a > b ? 1 : 0)
    : collator.compare(String(a), String(b));
  // `|| 0` normalises `-0` (from `-1 * 0`) and any stray NaN to a clean 0.
  return sign * base || 0;
}

function sortValueOf(col, row) {
  if (col.sortValue) return col.sortValue(row);
  if (col.value) return col.value(row);
  return undefined;
}

/** Sort a copy of `rows` by the column with `key === sortKey`. `sortDir` null
 *  (or an unknown key) returns `rows` untouched — the incoming server order. */
export function applySort(rows, columns, sortKey, sortDir) {
  if (!sortKey || !sortDir) return rows;
  const col = columns.find((c) => c.key === sortKey);
  if (!col) return rows;
  return [...rows].sort((r1, r2) => compareValues(sortValueOf(col, r1), sortValueOf(col, r2), sortDir));
}

/** Does one column's filter accept `row` for the currently selected `value`?
 *  An empty `value` means the filter is inactive and matches everything. */
export function filterMatches(col, row, value) {
  if (value == null || value === '') return true;
  const f = col.filter;
  if (f && typeof f === 'object' && typeof f.match === 'function') return f.match(row, value);
  const raw = col.value ? col.value(row) : undefined;
  const kind = typeof f === 'string' ? f : f && f.kind;
  if (kind === 'text') {
    return String(raw ?? '').toLowerCase().includes(String(value).toLowerCase());
  }
  return String(raw ?? '') === String(value);
}

/** Keep rows accepted by every active column filter. */
export function applyColumnFilters(filterColumns, rows, filterValues) {
  const active = filterColumns.filter((c) => {
    const v = filterValues[c.key];
    return v != null && v !== '';
  });
  if (active.length === 0) return rows;
  return rows.filter((row) => active.every((c) => filterMatches(c, row, filterValues[c.key])));
}

/** Apply the global search box. `search` is either a `(row, query) => boolean`
 *  predicate or `true` (substring match against every column that has `value`). */
export function applySearch(columns, rows, search, query) {
  if (!search) return rows;
  const q = String(query ?? '').trim();
  if (!q) return rows;
  if (typeof search === 'function') return rows.filter((row) => search(row, q));
  const ql = q.toLowerCase();
  const valueCols = columns.filter((c) => c.value);
  return rows.filter((row) => valueCols.some((c) => String(c.value(row) ?? '').toLowerCase().includes(ql)));
}

/** Distinct non-empty `value(row)` strings for a `filter: 'select'` shorthand column. */
export function distinctOptions(rows, col) {
  const set = new Set();
  for (const r of rows) {
    const raw = col.value ? col.value(r) : undefined;
    if (raw != null && raw !== '') set.add(String(raw));
  }
  return [...set].sort((x, y) => collator.compare(x, y)).map((v) => ({ value: v, label: v }));
}
