import { describe, it, expect } from 'vitest';
import {
  compareValues, applySort, filterMatches, applyColumnFilters, applySearch, distinctOptions
} from '../../src/lib/datatable.js';

describe('compareValues', () => {
  it('orders numbers numerically, not lexically', () => {
    expect([10, 2, 1].sort((a, b) => compareValues(a, b, 'asc'))).toEqual([1, 2, 10]);
    expect([10, 2, 1].sort((a, b) => compareValues(a, b, 'desc'))).toEqual([10, 2, 1]);
  });

  it('uses natural (numeric) ordering for strings with embedded numbers', () => {
    const rows = ['Pos 10', 'Pos 2', 'Pos 1'];
    expect(rows.sort((a, b) => compareValues(a, b, 'asc'))).toEqual(['Pos 1', 'Pos 2', 'Pos 10']);
  });

  it('folds German diacritics and case (Ä sorts as A, before B)', () => {
    const rows = ['Zebra', 'Äpfel', 'birne'];
    expect(rows.sort((a, b) => compareValues(a, b, 'asc'))).toEqual(['Äpfel', 'birne', 'Zebra']);
  });

  it('sorts nullish / empty values last regardless of direction', () => {
    expect(['b', null, 'a', ''].sort((x, y) => compareValues(x, y, 'asc'))).toEqual(['a', 'b', null, '']);
    const desc = ['b', null, 'a', ''].sort((x, y) => compareValues(x, y, 'desc'));
    expect(desc.slice(0, 2)).toEqual(['b', 'a']);
    expect(desc.slice(2).every((v) => v == null || v === '')).toBe(true);
  });

  it('returns 0 for equal keys', () => {
    expect(compareValues(5, 5, 'asc')).toBe(0);
    expect(compareValues('x', 'x', 'desc')).toBe(0);
  });
});

describe('applySort', () => {
  const columns = [{ key: 'n', value: (r) => r.n }, { key: 'label', sortValue: (r) => r.label }];

  it('returns the input untouched when no direction or unknown key', () => {
    const rows = [{ n: 3 }, { n: 1 }];
    expect(applySort(rows, columns, 'n', null)).toBe(rows);
    expect(applySort(rows, columns, 'missing', 'asc')).toBe(rows);
  });

  it('sorts a copy, leaving the original array order intact', () => {
    const rows = [{ n: 3 }, { n: 1 }, { n: 2 }];
    const sorted = applySort(rows, columns, 'n', 'asc');
    expect(sorted.map((r) => r.n)).toEqual([1, 2, 3]);
    expect(rows.map((r) => r.n)).toEqual([3, 1, 2]);
  });

  it('is stable for equal keys', () => {
    const rows = [
      { n: 1, id: 'a' }, { n: 1, id: 'b' }, { n: 0, id: 'c' }, { n: 1, id: 'd' }
    ];
    const sorted = applySort(rows, columns, 'n', 'asc');
    expect(sorted.map((r) => r.id)).toEqual(['c', 'a', 'b', 'd']);
  });

  it('honours sortValue over value', () => {
    const rows = [{ label: 'B' }, { label: 'A' }];
    expect(applySort(rows, columns, 'label', 'asc').map((r) => r.label)).toEqual(['A', 'B']);
  });
});

describe('filterMatches', () => {
  it('accepts every row when the filter value is empty', () => {
    const col = { filter: 'text', value: (r) => r.name };
    expect(filterMatches(col, { name: 'anything' }, '')).toBe(true);
    expect(filterMatches(col, { name: 'anything' }, null)).toBe(true);
  });

  it('does a case-insensitive substring match for text shorthand', () => {
    const col = { filter: 'text', value: (r) => r.name };
    expect(filterMatches(col, { name: 'Apfelsaft' }, 'apfel')).toBe(true);
    expect(filterMatches(col, { name: 'Apfelsaft' }, 'birne')).toBe(false);
  });

  it('does an exact string match for select shorthand', () => {
    const col = { filter: 'select', value: (r) => r.vault };
    expect(filterMatches(col, { vault: 'Keller' }, 'Keller')).toBe(true);
    expect(filterMatches(col, { vault: 'Keller' }, 'Kel')).toBe(false);
  });

  it('delegates to a custom match function', () => {
    const col = {
      filter: { kind: 'select', match: (r, v) => (v === 'none' ? r.cat == null : r.cat === Number(v)) }
    };
    expect(filterMatches(col, { cat: null }, 'none')).toBe(true);
    expect(filterMatches(col, { cat: 5 }, 'none')).toBe(false);
    expect(filterMatches(col, { cat: 5 }, '5')).toBe(true);
    expect(filterMatches(col, { cat: 5 }, '7')).toBe(false);
  });
});

describe('applyColumnFilters', () => {
  const rows = [
    { name: 'Apfel', cat: 1 },
    { name: 'Birne', cat: null },
    { name: 'Apfelmus', cat: 2 }
  ];
  const nameCol = { key: 'name', filter: 'text', value: (r) => r.name };
  const catCol = {
    key: 'cat',
    filter: { kind: 'select', match: (r, v) => (v === 'none' ? r.cat == null : r.cat === Number(v)) }
  };

  it('returns the same reference when no filter is active', () => {
    expect(applyColumnFilters([nameCol, catCol], rows, { name: '', cat: '' })).toBe(rows);
  });

  it('applies a single active filter', () => {
    expect(applyColumnFilters([nameCol, catCol], rows, { name: 'apfel', cat: '' }).map((r) => r.name))
      .toEqual(['Apfel', 'Apfelmus']);
  });

  it('ANDs multiple active filters, including the "none" bucket', () => {
    expect(applyColumnFilters([nameCol, catCol], rows, { name: 'b', cat: 'none' }).map((r) => r.name))
      .toEqual(['Birne']);
  });
});

describe('applySearch', () => {
  const rows = [
    { name: 'Apple Juice', vendor: 'Granini' },
    { name: 'Cola Zero', vendor: 'Coca' }
  ];
  const columns = [
    { key: 'name', value: (r) => r.name },
    { key: 'vendor', value: (r) => r.vendor }
  ];

  it('passes rows through when search is disabled or the query is blank', () => {
    expect(applySearch(columns, rows, false, 'apple')).toBe(rows);
    expect(applySearch(columns, rows, true, '   ')).toBe(rows);
  });

  it('matches against every column that has a value accessor (search: true)', () => {
    expect(applySearch(columns, rows, true, 'granini').map((r) => r.name)).toEqual(['Apple Juice']);
    expect(applySearch(columns, rows, true, 'cola').map((r) => r.name)).toEqual(['Cola Zero']);
  });

  it('uses a predicate when one is supplied', () => {
    const pred = (r, q) => r.name.toLowerCase().includes(q.toLowerCase());
    expect(applySearch(columns, rows, pred, 'zero').map((r) => r.name)).toEqual(['Cola Zero']);
  });
});

describe('distinctOptions', () => {
  it('dedupes, drops nullish/empty and sorts naturally', () => {
    const rows = [{ v: 'B' }, { v: 'a' }, { v: null }, { v: 'B' }, { v: '' }, { v: 'a' }];
    expect(distinctOptions(rows, { value: (r) => r.v })).toEqual([
      { value: 'a', label: 'a' },
      { value: 'B', label: 'B' }
    ]);
  });
});
