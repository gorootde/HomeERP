import { getStockSummary, getCategoryStockSummary } from './api.js';
import { escHtml, fmtQty } from './app.js';
import { t } from './i18n.js';

// Returns 'green' | 'yellow' | 'red' | 'gray'
function trafficStatus(total, min) {
  if (min == null) return 'gray';
  if (total >= min)        return 'green';
  if (total >= min * 0.5)  return 'yellow';
  return 'red';
}

function statusLabel(status) {
  return {
    green:  t('dashboard.status_ok'),
    yellow: t('dashboard.status_low'),
    red:    t('dashboard.status_critical'),
    gray:   t('dashboard.status_none'),
  }[status] ?? '—';
}

function renderCategoryCards(categories) {
  if (!categories.length) return '';

  const cards = categories.map(c => {
    const status = trafficStatus(c.total_quantity, c.min_stock_quantity);
    const unitAbbr = c.min_stock_unit ? ' ' + escHtml(c.min_stock_unit.abbreviation) : '';
    const stockLine = c.min_stock_quantity != null
      ? `${fmtQty(c.total_quantity)}${unitAbbr} <span class="cat-stock-sep">/</span> ${fmtQty(c.min_stock_quantity)}${unitAbbr}`
      : `${fmtQty(c.total_quantity)}${unitAbbr}`;

    return `
      <div class="cat-card cat-card--${status}">
        <div class="cat-card-header">
          <span class="traffic-light traffic-light--${status}"></span>
          <span class="cat-card-status">${statusLabel(status)}</span>
        </div>
        <div class="cat-card-name">${escHtml(c.category_name)}</div>
        <div class="cat-card-stock">${stockLine}</div>
        <div class="cat-card-meta">${c.product_count} Produkt${c.product_count !== 1 ? 'e' : ''}</div>

      </div>`;
  }).join('');

  return `
    <div class="section-header">
      <h2 class="section-title">${t('dashboard.section_by_category')}</h2>
    </div>
    <div class="cat-grid">${cards}</div>`;
}

export async function render() {
  const content = document.getElementById('app-content');

  const [summary, catSummary] = await Promise.all([getStockSummary(), getCategoryStockSummary()]);

  const totalProducts = summary.length;
  const totalUnits    = summary.reduce((s, i) => s + i.total_quantity, 0);
  const vaultSet      = new Set(summary.flatMap(i => i.by_vault.map(v => v.vault_id)));

  const criticalCount = catSummary.filter(c =>
    c.min_stock_quantity != null && c.total_quantity < c.min_stock_quantity * 0.5
  ).length;
  const warningCount = catSummary.filter(c =>
    c.min_stock_quantity != null &&
    c.total_quantity >= c.min_stock_quantity * 0.5 &&
    c.total_quantity < c.min_stock_quantity
  ).length;

  const rows = summary
    .sort((a, b) => b.total_quantity - a.total_quantity)
    .map(item => {
      const unitAbbr = item.unit ? ' ' + escHtml(item.unit.abbreviation) : '';
      const vaultPills = item.by_vault
        .sort((a, b) => b.total_quantity - a.total_quantity)
        .map(v => `<span class="badge badge-gray">${escHtml(v.vault_description)}: ${fmtQty(v.total_quantity)}</span>`)
        .join('');
      return `
        <tr>
          <td><span class="font-semibold">${escHtml(item.product_name)}</span></td>
          <td class="text-muted">${escHtml(item.vendor)}</td>
          <td class="text-muted">${escHtml(item.size)}${unitAbbr}</td>
          <td><span class="badge badge-blue">${fmtQty(item.total_quantity)}</span></td>
          <td><div class="ean-tags">${vaultPills}</div></td>
        </tr>`;
    }).join('');

  const emptyRow = `
    <tr>
      <td colspan="5">
        <div class="empty-state">
          <i data-lucide="package-open"></i>
          <p>${t('dashboard.empty')}</p>
        </div>
      </td>
    </tr>`;

  content.innerHTML = `
    <div class="page-header">
      <h1 class="page-title">${t('dashboard.title')}</h1>
    </div>

    <div class="stats-grid">
      <div class="card">
        <div class="card-title">${t('dashboard.products_in_stock')}</div>
        <div class="card-value">${totalProducts}</div>
      </div>
      <div class="card">
        <div class="card-title">${t('dashboard.total_stock')}</div>
        <div class="card-value">${fmtQty(totalUnits)}</div>
      </div>
      <div class="card">
        <div class="card-title">${t('dashboard.storage_locations')}</div>
        <div class="card-value">${vaultSet.size}</div>
      </div>
      ${criticalCount > 0 ? `
      <div class="card card--danger">
        <div class="card-title">${t('dashboard.critical')}</div>
        <div class="card-value">${criticalCount} ${t('dashboard.cat_suffix')}</div>
      </div>` : ''}
      ${warningCount > 0 ? `
      <div class="card card--warning">
        <div class="card-title">${t('dashboard.low')}</div>
        <div class="card-value">${warningCount} ${t('dashboard.cat_suffix')}</div>
      </div>` : ''}
    </div>

    ${renderCategoryCards(catSummary)}

    <div class="section-header">
      <h2 class="section-title">${t('dashboard.section_all_products')}</h2>
    </div>
    <div class="table-container">
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>${t('dashboard.col_product')}</th>
              <th>${t('dashboard.col_vendor')}</th>
              <th>${t('dashboard.col_size')}</th>
              <th>${t('dashboard.col_total_qty')}</th>
              <th>${t('dashboard.col_by_vault')}</th>
            </tr>
          </thead>
          <tbody>${rows || emptyRow}</tbody>
        </table>
      </div>
    </div>`;
}
