export function fmtQty(n) {
  if (n == null) return '—';
  return Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/\.?0+$/, '');
}

export function fmtDate(d) {
  if (!d) return '—';
  const date = typeof d === 'string' ? new Date(d + 'T00:00:00') : new Date(d);
  return date.toLocaleDateString('de-DE', { year: 'numeric', month: '2-digit', day: '2-digit' });
}

export function fmtFactor(n) {
  if (n == null) return '';
  return Number.isInteger(n) ? String(n) : Number(n).toFixed(4).replace(/\.?0+$/, '');
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

export function isExpiringSoon(dateStr, days) {
  if (!dateStr) return false;
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const bbd = new Date(dateStr);
  const cutoff = new Date(now);
  cutoff.setDate(cutoff.getDate() + days);
  return bbd >= now && bbd <= cutoff;
}
