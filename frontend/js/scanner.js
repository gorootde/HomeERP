import {
  getSettings,
  getByEan, createProduct, setImageFromUrl,
  getVaults, getUnits, getCategories,
  createStockEntry, updateStockEntry, deleteStockEntry,
  getStockEntryByStockId, getEanInfo,
} from './api.js';
import { openModal, showToast, escHtml, fmtQty, fmtDate } from './app.js';
import { t } from './i18n.js';

let _scanner = null;
let _settings = { mode: 'manual', prefix: '', counter: '0', padLength: '0' };

export async function render() {
  const content = document.getElementById('app-content');

  // Load settings so we can detect Stock IDs by prefix
  try {
    const all = await getSettings();
    const get = (key) => all.find(s => s.key === key)?.value ?? '';
    _settings = {
      mode:      get('stock_id_mode'),
      prefix:    get('stock_id_prefix'),
      counter:   get('stock_id_counter'),
      padLength: get('stock_id_pad_length'),
    };
  } catch (_) {}

  content.innerHTML = `
    <div class="page-header">
      <h1 class="page-title">${t('scanner.title')}</h1>
    </div>
    <div class="scanner-container">
      <div id="qr-reader"></div>
      <div id="scan-status" class="text-muted text-sm mt-4" style="text-align:center">
        ${t('scanner.status_starting')}
      </div>
      <div id="scan-result"></div>
    </div>`;

  await startScanner();
}

async function startScanner() {
  const status = document.getElementById('scan-status');

  if (!window.Html5Qrcode) {
    if (status) status.textContent = t('scanner.err_lib_not_loaded');
    return;
  }

  if (_scanner) {
    try { if (_scanner.isScanning) await _scanner.stop(); } catch (_) {}
    _scanner = null;
  }

  _scanner = new Html5Qrcode('qr-reader');

  if (!navigator.mediaDevices?.getUserMedia) {
    if (status) status.innerHTML = `<span style="color:var(--color-danger)">${t('scanner.err_camera_api')}</span>`;
    return;
  }

  try {
    await _scanner.start(
      { facingMode: 'environment' },
      { fps: 10, qrbox: { width: 280, height: 140 } },
      onScanSuccess,
      () => {}
    );
    if (status) status.textContent = t('scanner.status_active');
  } catch (err) {
    _scanner = null;
    if (status) {
      const msg = String(err?.message ?? err);
      const isDenied = err?.name === 'NotAllowedError' || err?.name === 'PermissionDeniedError' || msg.includes('NotAllowedError');
      status.innerHTML = isDenied
        ? `<span style="color:var(--color-danger)">${t('scanner.err_camera_denied')}</span>`
        : `<span style="color:var(--color-danger)">${t('scanner.err_camera_unavailable', { msg: escHtml(msg) })}</span>`;
    }
  }
}

function isStockId(code) {
  if (_settings.mode !== 'generated') return false;
  const prefix = _settings.prefix ?? '';
  if (!prefix) return false;
  return code.startsWith(prefix);
}

async function onScanSuccess(decodedText) {
  if (!_scanner) return;
  try { await _scanner.pause(true); } catch (_) {}

  const resultEl = document.getElementById('scan-result');
  const statusEl = document.getElementById('scan-status');
  if (!resultEl) return;

  resultEl.innerHTML = `<div class="scan-result-card"><div class="text-muted text-sm">${t('scanner.status_searching', { code: escHtml(decodedText) })}</div></div>`;

  if (isStockId(decodedText)) {
    await handleStockIdScan(decodedText, resultEl, statusEl);
  } else {
    await handleEanScan(decodedText, resultEl, statusEl);
  }
}

// ── Flow A: Stock ID ─────────────────────────────────────────────────────────

async function handleStockIdScan(code, resultEl, statusEl) {
  try {
    const entry = await getStockEntryByStockId(code);

    const bbd = entry.best_before_date;
    const bbdStr = bbd
      ? `<span class="badge ${new Date(bbd) < new Date() ? 'badge-red' : 'badge-green'}">${fmtDate(bbd)}</span>`
      : '<span class="text-muted">—</span>';

    if (statusEl) statusEl.textContent = t('scanner.stockid_found', { name: entry.product.name });

    resultEl.innerHTML = `
      <div class="scan-result-card">
        <div class="scan-badge scan-badge--stockid"><i data-lucide="qr-code"></i> ${t('scanner.stockid_badge')}</div>
        <div class="product-name">${escHtml(entry.product.name)}</div>
        <div class="product-meta">${escHtml(entry.product.vendor)} · ${escHtml(entry.product.size)}</div>
        <div class="scan-meta-row">
          <span class="text-muted text-sm">${t('scanner.label_location')}</span>
          <span>${escHtml(entry.vault.description)}</span>
        </div>
        <div class="scan-meta-row">
          <span class="text-muted text-sm">${t('scanner.label_stock')}</span>
          <span class="badge badge-blue">${fmtQty(entry.quantity)}</span>
        </div>
        <div class="scan-meta-row">
          <span class="text-muted text-sm">${t('scanner.label_bbd')}</span>
          ${bbdStr}
        </div>
        <div class="scan-actions">
          <button class="btn btn-danger" id="btn-consume">
            <i data-lucide="minus-circle"></i> ${t('scanner.btn_consume')}
          </button>
          <button class="btn btn-ghost" id="btn-adjust">
            <i data-lucide="sliders-horizontal"></i> ${t('scanner.btn_adjust')}
          </button>
        </div>
        <div style="margin-top:12px">
          <button class="btn btn-ghost btn-sm" id="btn-resume-scan">
            <i data-lucide="scan-barcode"></i> ${t('scanner.btn_continue')}
          </button>
        </div>
      </div>`;

    lucide.createIcons();

    resultEl.querySelector('#btn-resume-scan').addEventListener('click', resumeScanner);

    resultEl.querySelector('#btn-consume').addEventListener('click', async () => {
      try {
        if (entry.quantity <= 1) {
          await deleteStockEntry(entry.id);
          showToast(t('scanner.toast_consumed_deleted', { name: entry.product.name }));
        } else {
          await updateStockEntry(entry.id, { quantity: entry.quantity - 1 });
          showToast(t('scanner.toast_consumed', { name: entry.product.name }));
        }
        resumeScanner();
      } catch (err) {
        showToast(err.message, 'error');
      }
    });

    resultEl.querySelector('#btn-adjust').addEventListener('click', () => {
      showAdjustModal(entry, () => resumeScanner());
    });

  } catch (err) {
    if (err.status === 404) {
      resultEl.innerHTML = `
        <div class="scan-unknown">
          <strong>${t('scanner.stockid_not_found', { code: escHtml(code) })}</strong><br/>
          <span class="text-sm text-muted">${t('scanner.stockid_not_found_hint')}</span>
        </div>
        <div style="margin-top:12px">
          <button class="btn btn-ghost btn-sm" id="btn-resume-scan">
            <i data-lucide="scan-barcode"></i> ${t('scanner.btn_continue')}
          </button>
        </div>`;
      lucide.createIcons();
      resultEl.querySelector('#btn-resume-scan').addEventListener('click', resumeScanner);
    } else {
      showToast(err.message, 'error');
      resumeScanner();
    }
  }
}

function showAdjustModal(entry, onDone) {
  const { overlay, close } = openModal(
    t('scanner.adjust_modal_title', { name: escHtml(entry.product.name) }),
    `<div class="form-field">
       <label for="adj-qty">${t('scanner.label_new_qty')}</label>
       <input id="adj-qty" type="number" min="0.01" step="0.01" value="${entry.quantity}" />
     </div>
     <div class="form-actions">
       <button type="button" class="btn btn-ghost" id="adj-cancel">${t('common.cancel')}</button>
       <button type="button" class="btn btn-primary" id="adj-save">${t('common.save')}</button>
     </div>`
  );
  lucide.createIcons();

  const input = overlay.querySelector('#adj-qty');
  overlay.querySelector('#adj-cancel').addEventListener('click', close);
  overlay.querySelector('#adj-save').addEventListener('click', async () => {
    const qty = parseFloat(input.value);
    if (isNaN(qty) || qty <= 0) { showToast(t('scanner.err_invalid_qty'), 'error'); return; }
    try {
      await updateStockEntry(entry.id, { quantity: qty });
      showToast(t('scanner.toast_qty_updated'));
      close();
      onDone();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
  input.focus();
  input.select();
}

// ── Flow B: EAN ──────────────────────────────────────────────────────────────

async function handleEanScan(ean, resultEl, statusEl) {
  try {
    const product = await getByEan(ean);
    if (statusEl) statusEl.textContent = t('scanner.ean_found', { name: product.name });
    showNewStockEntryModal(product, null, () => resumeScanner());
    resumeWithoutClear();
  } catch (err) {
    if (err.status === 404) {
      if (statusEl) statusEl.textContent = t('scanner.ean_unknown_status', { ean });
      resultEl.innerHTML = `
        <div class="scan-unknown">
          <strong>${t('scanner.ean_unknown_heading')}</strong> <span class="font-mono">${escHtml(ean)}</span><br/>
          <span class="text-sm text-muted">${t('scanner.ean_unknown_hint')}</span>
        </div>
        <div class="scan-actions" style="margin-top:12px">
          <button class="btn btn-primary" id="btn-create-product">
            <i data-lucide="plus"></i> ${t('scanner.btn_new_product')}
          </button>
        </div>
        <div style="margin-top:8px">
          <button class="btn btn-ghost btn-sm" id="btn-resume-scan">
            <i data-lucide="scan-barcode"></i> ${t('scanner.btn_continue')}
          </button>
        </div>`;
      lucide.createIcons();
      resultEl.querySelector('#btn-resume-scan').addEventListener('click', resumeScanner);
      resultEl.querySelector('#btn-create-product').addEventListener('click', () => {
        showNewProductModal(ean, () => resumeScanner());
      });
    } else {
      showToast(err.message, 'error');
      resumeScanner();
    }
  }
}

async function showNewProductModal(prefillEan, onDone) {
  let units = [], categories = [], offRaw = null;
  try {
    [units, categories, offRaw] = await Promise.all([
      getUnits(),
      getCategories(),
      getEanInfo(prefillEan),
    ]);
  } catch (_) {}

  // Treat an all-null result (nothing found) the same as null.
  // Strip non-numeric characters from OFF size (e.g. "500 g" → "500").
  const offSize = offRaw?.size ? offRaw.size.replace(/[^\d.,]/g, '').replace(',', '.') || null : null;
  const off = (offRaw?.name || offRaw?.vendor || offSize || offRaw?.image_url)
    ? { name: offRaw.name, vendor: offRaw.vendor, size: offSize, imageUrl: offRaw.image_url }
    : null;

  const unitOpts = units.map(u =>
    `<option value="${u.id}">${escHtml(u.name)} (${escHtml(u.abbreviation)})</option>`
  ).join('');

  const catOpts = categories.map(c =>
    `<option value="${c.id}">${escHtml(c.name)}</option>`
  ).join('');

  const offBanner = off ? `
    <div class="off-prefill-banner">
      ${off.imageUrl ? `<img class="off-prefill-thumb" src="${escHtml(off.imageUrl)}" alt="" />` : ''}
      <div>
        <span class="off-prefill-label"><i data-lucide="sparkles"></i> ${t('scanner.off_banner_label')}</span>
        <span class="text-muted text-sm" style="display:block">${t('scanner.off_banner_hint')}</span>
      </div>
    </div>` : '';

  const { overlay, close } = openModal(
    t('scanner.new_product_modal'),
    `${offBanner}
     <form id="np-form">
       <div class="form-field">
         <label for="np-name">${t('scanner.label_name')}</label>
         <input id="np-name" name="name" type="text" required placeholder="${t('scanner.placeholder_name')}"
           value="${escHtml(off?.name ?? '')}" />
       </div>
       <div class="form-row">
         <div class="form-field">
           <label for="np-vendor">${t('scanner.label_vendor')}</label>
           <input id="np-vendor" name="vendor" type="text" placeholder="${t('scanner.placeholder_vendor')}"
             value="${escHtml(off?.vendor ?? '')}" />
         </div>
         <div class="form-field">
           <label for="np-size">${t('scanner.label_size')}</label>
           <input id="np-size" name="size" type="number" min="0" step="any" placeholder="${t('scanner.placeholder_size')}"
             value="${escHtml(off?.size ?? '')}" />
         </div>
       </div>
       <div class="form-row">
         <div class="form-field">
           <label for="np-unit">${t('scanner.label_unit')}</label>
           <select id="np-unit" name="unit_id" required>
             <option value="" disabled selected>${t('scanner.unit_placeholder')}</option>
             ${unitOpts}
           </select>
         </div>
         <div class="form-field">
           <label for="np-category">${t('scanner.label_category')}</label>
           <select id="np-category" name="category_id">
             <option value="">${t('common.no_category')}</option>
             ${catOpts}
           </select>
         </div>
       </div>
       <div class="form-field">
         <label for="np-ean">${t('scanner.label_ean')}</label>
         <input id="np-ean" name="ean" type="text" value="${escHtml(prefillEan ?? '')}" placeholder="${t('scanner.placeholder_ean')}" />
         <span class="form-hint">${t('scanner.ean_hint')}</span>
       </div>
       <div class="form-actions">
         <button type="button" class="btn btn-ghost" id="np-cancel">${t('common.cancel')}</button>
         <button type="submit" class="btn btn-primary">${t('scanner.btn_create_product')}</button>
       </div>
     </form>`
  );
  lucide.createIcons();

  overlay.querySelector('#np-cancel').addEventListener('click', () => { close(); onDone(); });
  overlay.querySelector('#np-form').addEventListener('submit', async e => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = {
      name:        fd.get('name').trim(),
      vendor:      fd.get('vendor').trim() || '-',
      size:        fd.get('size').trim() || '-',
      unit_id:     Number(fd.get('unit_id')),
      category_id: Number(fd.get('category_id')) || null,
      ean_codes:   [],
    };
    const ean = fd.get('ean').trim();
    if (ean) data.ean_codes = [ean];
    try {
      const product = await createProduct(data);
      if (off?.imageUrl) {
        try { await setImageFromUrl(product.id, off.imageUrl); } catch (_) {}
      }
      showToast(t('scanner.toast_product_created', { name: product.name }));
      close();
      // Immediately offer to add a stock entry for the new product
      showNewStockEntryModal(product, null, onDone);
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

async function showNewStockEntryModal(product, prefillVaultId, onDone) {
  let vaults = [];
  try { vaults = await getVaults(); } catch (_) {}

  const vaultOpts = vaults.map(v =>
    `<option value="${v.id}" ${prefillVaultId === v.id ? 'selected' : ''}>${escHtml(v.description)}</option>`
  ).join('');

  const { overlay, close } = openModal(
    t('scanner.stock_entry_modal'),
    `<div class="scan-product-info mb-4">
       <div class="font-semibold">${escHtml(product.name)}</div>
       <div class="text-muted text-sm">${escHtml(product.vendor ?? '')}${product.vendor && product.size ? ' · ' : ''}${escHtml(product.size ?? '')}</div>
     </div>
     <form id="se-form">
       <div class="form-field">
         <label for="se-vault">${t('scanner.label_vault')}</label>
         <select id="se-vault" name="vault_id" required>
           <option value="">${t('scanner.select_vault')}</option>
           ${vaultOpts}
         </select>
       </div>
       <div class="form-row">
         <div class="form-field">
           <label for="se-qty">${t('scanner.label_qty')}</label>
           <input id="se-qty" name="quantity" type="number" min="0.01" step="0.01" value="1" required />
         </div>
         <div class="form-field">
           <label for="se-bbd">${t('scanner.label_bbd_form')}</label>
           <input id="se-bbd" name="best_before_date" type="date" />
         </div>
       </div>
       <div class="form-field">
         <label for="se-comment">${t('scanner.label_comment')}</label>
         <input id="se-comment" name="comment" type="text" placeholder="${t('scanner.placeholder_comment')}" />
       </div>
       <div class="form-actions">
         <button type="button" class="btn btn-ghost" id="se-cancel">${t('common.cancel')}</button>
         <button type="submit" class="btn btn-primary">${t('scanner.btn_add_entry')}</button>
       </div>
     </form>`
  );
  lucide.createIcons();

  overlay.querySelector('#se-cancel').addEventListener('click', () => { close(); onDone(); });
  overlay.querySelector('#se-form').addEventListener('submit', async e => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = {
      product_id:       product.id,
      vault_id:         Number(fd.get('vault_id')),
      quantity:         parseFloat(fd.get('quantity')),
      best_before_date: fd.get('best_before_date') || null,
      comment:          fd.get('comment').trim() || null,
    };
    try {
      await createStockEntry(data);
      showToast(t('scanner.toast_entry_created', { name: product.name }));
      close();
      onDone();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function resumeScanner() {
  const statusEl = document.getElementById('scan-status');
  const resultEl = document.getElementById('scan-result');
  if (resultEl) resultEl.innerHTML = '';
  if (statusEl) statusEl.textContent = t('scanner.status_active');
  try { _scanner?.resume(); } catch (_) {}
}

// Resume scanning without clearing the result panel (used when a modal opens)
function resumeWithoutClear() {
  try { _scanner?.resume(); } catch (_) {}
}

export async function cleanup() {
  if (_scanner) {
    try {
      if (_scanner.isScanning) await _scanner.stop();
    } catch (_) {}
    _scanner = null;
  }
}
