export function fmtQty(n) {
  if (n == null) return '—';
  return Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/\.?0+$/, '');
}

export function fmtDate(d) {
  if (!d) return '—';
  const date = typeof d === 'string' ? new Date(d + 'T00:00:00') : new Date(d);
  return date.toLocaleDateString('de-DE', { year: 'numeric', month: '2-digit', day: '2-digit' });
}

export function fmtDateTime(d) {
  if (!d) return '—';
  const date = new Date(d);
  if (isNaN(date)) return '—';
  return date.toLocaleString('de-DE', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit'
  });
}

export function fmtProductLabel(p) {
  if (!p) return '';
  let label = p.name;
  if (p.vendor) label += ` - ${p.vendor}`;
  return label;
}

export function fmtFactor(n) {
  if (n == null) return '';
  return Number.isInteger(n) ? String(n) : Number(n).toFixed(4).replace(/\.?0+$/, '');
}

// Resolves a UnitConversionEditor onadd() payload into a { factor, base_unit_id, base_unit }
// triple, following the to_unit_id chain through another product-specific conversion
// (to_unit_id === "puc_<id>") down to a real global unit — same math regardless of
// whether the referenced puc row is already persisted or still staged client-side.
export function resolveUnitConversion({ factor, to_unit_id, units, pucUnits }) {
  let resolvedFactor = factor;
  let resolvedBaseUnitId = Number(to_unit_id);
  let resolvedBaseUnit = units.find(u => u.id === resolvedBaseUnitId);

  if (String(to_unit_id).startsWith('puc_')) {
    const pucKey = String(to_unit_id).slice(4);
    const ref = pucUnits.find(c => String(c.id) === pucKey);
    if (!ref) return null;
    resolvedFactor = factor * ref.factor;
    resolvedBaseUnitId = ref.base_unit.id;
    resolvedBaseUnit = ref.base_unit;
  }
  return { factor: resolvedFactor, base_unit_id: resolvedBaseUnitId, base_unit: resolvedBaseUnit };
}

// Builds a not-yet-persisted product-unit-conversion row (client-side temp id) for staging
// in a "New Product" form, before the product itself has an id to POST conversions against.
export function stagePucConversion({ factor, to_unit_id, name, units, pucUnits }) {
  const resolved = resolveUnitConversion({ factor, to_unit_id, units, pucUnits });
  if (!resolved) return null;
  return {
    id: 'staged-' + crypto.randomUUID(),
    unit_name: name,
    name,
    factor: resolved.factor,
    base_unit_id: resolved.base_unit_id,
    base_unit: resolved.base_unit,
    to_unit: resolved.base_unit
  };
}

export function escHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function trafficStatus(total, min) {
  if (min == null || min === 0) return 'none';
  if (total <= 0) return 'critical';
  if (total < min) return 'low';
  return 'ok';
}

export function parseSizeString(sizeStr) {
  if (!sizeStr) return { numeric: '', unitAbbr: '' };
  const match = sizeStr.trim().match(/^([\d.,]+)\s*([a-zA-Z]+)/);
  if (match) return { numeric: match[1], unitAbbr: match[2].toLowerCase() };
  return { numeric: sizeStr, unitAbbr: '' };
}

export function isStockId(code) {
  // A pure-digit code is an EAN/barcode, anything else (e.g. "INV0033") is a
  // stock ID — independent of the configured stock_id_mode.
  return !/^\d+$/.test(code.trim());
}

export function isExpiringSoon(dateStr, days) {
  if (!dateStr) return false;
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const bbd = new Date(dateStr);
  const cutoff = new Date(now);
  cutoff.setDate(cutoff.getDate() + days);
  return bbd >= now && bbd <= cutoff;
}
