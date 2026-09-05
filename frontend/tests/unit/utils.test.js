import { describe, it, expect } from 'vitest';
import { parseSizeString, matchUnitFromOffSize, fmtEntryQty } from '../../src/lib/utils.js';

describe('parseSizeString', () => {
  it('parses a simple "amount unit" string', () => {
    expect(parseSizeString('200 g')).toEqual({ numeric: '200', unitAbbr: 'g' });
  });

  it('parses decimal amounts with a dot or a comma', () => {
    expect(parseSizeString('0.33 l')).toEqual({ numeric: '0.33', unitAbbr: 'l' });
    expect(parseSizeString('0,33 l')).toEqual({ numeric: '0,33', unitAbbr: 'l' });
  });

  it('parses an amount and unit with no space between them', () => {
    expect(parseSizeString('1l')).toEqual({ numeric: '1', unitAbbr: 'l' });
  });

  it('resolves a multipack string to the per-item amount, not the pack count', () => {
    expect(parseSizeString('6x50g')).toEqual({ numeric: '50', unitAbbr: 'g' });
    expect(parseSizeString('6 x 50 g')).toEqual({ numeric: '50', unitAbbr: 'g' });
  });

  it('returns empty fields for empty/missing input', () => {
    expect(parseSizeString('')).toEqual({ numeric: '', unitAbbr: '' });
    expect(parseSizeString(null)).toEqual({ numeric: '', unitAbbr: '' });
    expect(parseSizeString(undefined)).toEqual({ numeric: '', unitAbbr: '' });
  });

  it('falls back to returning the raw string when it cannot be parsed', () => {
    expect(parseSizeString('unbekannt')).toEqual({ numeric: 'unbekannt', unitAbbr: '' });
  });
});

describe('matchUnitFromOffSize', () => {
  const units = [
    { id: 1, name: 'Gramm', abbreviation: 'g' },
    { id: 2, name: 'Liter', abbreviation: 'l' },
  ];

  it('matches "200 g" to the Gramm unit — the OFF -> new-product-dialog case', () => {
    const { numeric, matchedUnit } = matchUnitFromOffSize(units, '200 g');
    expect(numeric).toBe('200');
    expect(matchedUnit).toEqual({ id: 1, name: 'Gramm', abbreviation: 'g' });
  });

  it('matches "0.33 l" to the Liter unit', () => {
    const { numeric, matchedUnit } = matchUnitFromOffSize(units, '0.33 l');
    expect(numeric).toBe('0.33');
    expect(matchedUnit).toEqual({ id: 2, name: 'Liter', abbreviation: 'l' });
  });

  it('matches case-insensitively', () => {
    const { matchedUnit } = matchUnitFromOffSize(units, '200 G');
    expect(matchedUnit?.id).toBe(1);
  });

  it('resolves a multipack size to the per-item unit', () => {
    const { numeric, matchedUnit } = matchUnitFromOffSize(units, '6x50g');
    expect(numeric).toBe('50');
    expect(matchedUnit?.id).toBe(1);
  });

  it('leaves matchedUnit null when no configured unit has that abbreviation', () => {
    const { numeric, matchedUnit } = matchUnitFromOffSize(units, '5 stk');
    expect(numeric).toBe('5');
    expect(matchedUnit).toBeNull();
  });

  it('returns null/empty for a missing size', () => {
    expect(matchUnitFromOffSize(units, null)).toEqual({ numeric: '', matchedUnit: null });
  });
});

describe('fmtEntryQty', () => {
  const units = [
    { id: 2, name: 'Liter', abbreviation: 'L' },
    { id: 5, name: 'Milliliter', abbreviation: 'ml' },
  ];
  const product = {
    unit: { id: 2, abbreviation: 'L' },
    unit_conversions: [{ id: 7, unit_name: 'Kasten', factor: 12 }],
  };

  it('shows the picked unit with the base amount in parentheses (puc)', () => {
    const entry = { quantity: 12, entry_unit_key: 'puc_7', entry_quantity: 1, product };
    expect(fmtEntryQty(entry, units)).toBe('1 Kasten (12 L)');
  });

  it('shows a global unit the entry was created in', () => {
    const entry = { quantity: 0.5, entry_unit_key: 'global_5', entry_quantity: 500, product };
    expect(fmtEntryQty(entry, units)).toBe('500 ml (0.5 L)');
  });

  it('falls back to plain base unit for base-unit entries', () => {
    const entry = { quantity: 5, entry_unit_key: 'base', entry_quantity: 5, product };
    expect(fmtEntryQty(entry, units)).toBe('5 L');
  });

  it('falls back to plain base unit for legacy entries with no entry unit', () => {
    const entry = { quantity: 12, entry_unit_key: null, entry_quantity: null, product };
    expect(fmtEntryQty(entry, units)).toBe('12 L');
  });

  it('falls back when the referenced conversion no longer exists', () => {
    const entry = { quantity: 12, entry_unit_key: 'puc_99', entry_quantity: 1, product };
    expect(fmtEntryQty(entry, units)).toBe('12 L');
  });
});
