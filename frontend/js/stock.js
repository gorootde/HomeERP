import { getStockEntries, createStockEntry, updateStockEntry, deleteStockEntry, getProducts, getVaults, getTags, addTagToStockEntry, removeTagFromStockEntry, addStockId, removeStockId } from './api.js';
import { openModal, openConfirm, showToast, escHtml, fmtQty, fmtDate, buildTagsSection, attachTagListeners } from './app.js';
import { t } from './i18n.js';

let _allTags = [];

export async function render() {
  const content = document.getElementById('app-content');

  const [entries, products, vaults] = await Promise.all([
    getStockEntries({ limit: 500 }),
    getProducts(),
    getVaults(),
    getTags().then(t => { _allTags = t; }),
  ]);

  renderView(content, entries, products, vaults);
}

function renderTagChips(tags) {
  if (!tags || tags.length === 0) return '';
  return tags.map(t => `<span class="item-tag item-tag--sm">${escHtml(t.name)}</span>`).join('');
}

function renderStockIdChips(stockIds) {
  if (!stockIds || !stockIds.length) return '';
  return stockIds.map(s => `<span class="ean-tag font-mono text-xs">${escHtml(s.code)}</span>`).join('');
}

function renderView(content, entries, products, vaults) {
  const rows = entries.map(e => {
    const bbd = e.best_before_date;
    const isExpired = bbd && new Date(bbd) < new Date();
    const bbdCell = bbd
      ? `<span class="badge ${isExpired ? 'badge-red' : 'badge-green'}">${fmtDate(bbd)}</span>`
      : '<span class="text-muted">—</span>';

    const tagChips = renderTagChips(e.tags);
    const qrChips  = renderStockIdChips(e.stock_ids);
    const unitAbbr = e.product.unit ? ' ' + escHtml(e.product.unit.abbreviation) : '';
    return `
      <tr>
        <td>
          <div class="font-semibold">${escHtml(e.product.name)}</div>
          <div class="text-muted text-sm">${escHtml(e.product.vendor)} · ${escHtml(e.product.size)}${unitAbbr}</div>
          ${tagChips ? `<div class="item-tags mt-1">${tagChips}</div>` : ''}
        </td>
        <td class="text-muted">${escHtml(e.vault.description)}</td>
        <td><span class="badge badge-blue">${fmtQty(e.quantity)}</span></td>
        <td>${bbdCell}</td>
        <td class="text-muted text-sm">${escHtml(e.comment ?? '')}</td>
        <td>${qrChips || '<span class="text-muted">—</span>'}</td>
        <td>
          <div class="td-actions">
            <button class="btn btn-ghost btn-sm" data-edit="${e.id}"><i data-lucide="pencil"></i></button>
            <button class="btn btn-ghost btn-sm" data-qr="${e.id}" title="QR Codes"><i data-lucide="qr-code"></i></button>
            <button class="btn btn-danger btn-sm" data-delete="${e.id}"><i data-lucide="trash-2"></i></button>
          </div>
        </td>
      </tr>`;
  }).join('');

  const emptyRow = `
    <tr><td colspan="7">
      <div class="empty-state"><i data-lucide="layers"></i><p>${t('stock.empty')}</p></div>
    </td></tr>`;

  content.innerHTML = `
    <div class="page-header">
      <h1 class="page-title">${t('stock.title')}</h1>
      <div class="page-header-actions">
        <button class="btn btn-primary" id="btn-add-entry">
          <i data-lucide="plus"></i> ${t('stock.btn_add')}
        </button>
      </div>
    </div>

    <div class="filter-bar">
      <select id="filter-vault">
        <option value="">${t('stock.filter_all_vaults')}</option>
        ${vaults.map(v => `<option value="${v.id}">${escHtml(v.description)}</option>`).join('')}
      </select>
      <select id="filter-product">
        <option value="">${t('stock.filter_all_products')}</option>
        ${products.map(p => `<option value="${p.id}">${escHtml(p.name)}</option>`).join('')}
      </select>
    </div>

    <div class="table-container">
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>${t('stock.col_product')}</th>
              <th>${t('stock.col_vault')}</th>
              <th>${t('stock.col_qty')}</th>
              <th>${t('stock.col_bbd')}</th>
              <th>${t('stock.col_comment')}</th>
              <th>${t('stock.col_stockids')}</th>
              <th></th>
            </tr>
          </thead>
          <tbody id="entries-tbody">${rows || emptyRow}</tbody>
        </table>
      </div>
    </div>`;

  // ── Filter logic ─────────────────────────────────────────────────────────
  const applyFilter = () => {
    const vaultId   = Number(document.getElementById('filter-vault').value)   || null;
    const productId = Number(document.getElementById('filter-product').value) || null;
    const filtered  = entries.filter(e =>
      (!vaultId   || e.vault_id   === vaultId) &&
      (!productId || e.product_id === productId)
    );
    rebuildRows(filtered);
  };

  document.getElementById('filter-vault').addEventListener('change', applyFilter);
  document.getElementById('filter-product').addEventListener('change', applyFilter);

  document.getElementById('btn-add-entry').addEventListener('click', () => {
    showEntryModal(null, products, vaults);
  });

  attachEntryListeners(content, entries, products, vaults);
}

function rebuildRows(entries) {
  const tbody = document.getElementById('entries-tbody');
  if (!tbody) return;
  if (!entries.length) {
    tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><i data-lucide="layers"></i><p>${t('stock.empty_filter')}</p></div></td></tr>`;
    lucide.createIcons();
    return;
  }
  tbody.innerHTML = entries.map(e => {
    const bbd = e.best_before_date;
    const isExpired = bbd && new Date(bbd) < new Date();
    const bbdCell = bbd
      ? `<span class="badge ${isExpired ? 'badge-red' : 'badge-green'}">${fmtDate(bbd)}</span>`
      : '<span class="text-muted">—</span>';
    const tagChips = renderTagChips(e.tags);
    const qrChips  = renderStockIdChips(e.stock_ids);
    const unitAbbr = e.product.unit ? ' ' + escHtml(e.product.unit.abbreviation) : '';
    return `
      <tr>
        <td>
          <div class="font-semibold">${escHtml(e.product.name)}</div>
          <div class="text-muted text-sm">${escHtml(e.product.vendor)} · ${escHtml(e.product.size)}${unitAbbr}</div>
          ${tagChips ? `<div class="item-tags mt-1">${tagChips}</div>` : ''}
        </td>
        <td class="text-muted">${escHtml(e.vault.description)}</td>
        <td><span class="badge badge-blue">${fmtQty(e.quantity)}</span></td>
        <td>${bbdCell}</td>
        <td class="text-muted text-sm">${escHtml(e.comment ?? '')}</td>
        <td>${qrChips || '<span class="text-muted">—</span>'}</td>
        <td>
          <div class="td-actions">
            <button class="btn btn-ghost btn-sm" data-edit="${e.id}"><i data-lucide="pencil"></i></button>
            <button class="btn btn-ghost btn-sm" data-qr="${e.id}" title="QR Codes"><i data-lucide="qr-code"></i></button>
            <button class="btn btn-danger btn-sm" data-delete="${e.id}"><i data-lucide="trash-2"></i></button>
          </div>
        </td>
      </tr>`;
  }).join('');
  lucide.createIcons();
}

function attachEntryListeners(content, entries, products, vaults) {
  content.querySelectorAll('[data-edit]').forEach(btn => {
    const entry = entries.find(e => e.id === Number(btn.dataset.edit));
    btn.addEventListener('click', () => entry && showEntryModal(entry, products, vaults));
  });

  content.querySelectorAll('[data-qr]').forEach(btn => {
    const entry = entries.find(e => e.id === Number(btn.dataset.qr));
    btn.addEventListener('click', () => entry && showStockIdModal(entry));
  });

  content.querySelectorAll('[data-delete]').forEach(btn => {
    const id = Number(btn.dataset.delete);
    btn.addEventListener('click', () => {
      openConfirm(t('stock.confirm_delete'), async () => {
        try {
          await deleteStockEntry(id);
          showToast(t('stock.toast_deleted'));
          render();
        } catch (err) {
          showToast(err.message, 'error');
        }
      });
    });
  });
}

function showStockIdModal(entry) {
  const buildList = (ids) =>
    ids.map(s => `
      <span class="ean-tag" data-sid="${s.id}">
        <span class="font-mono">${escHtml(s.code)}</span>
        <button type="button" title="Entfernen" data-remove-sid="${s.id}">
          <i data-lucide="x"></i>
        </button>
      </span>`).join('');

  const { overlay, close } = openModal(
    `${t('stock.stockid_modal_title', { name: escHtml(entry.product.name) })}`,
    `<p class="text-muted text-sm mb-4">${t('stock.stockid_modal_hint')}</p>
     <div class="ean-manager">
       <div class="ean-manager-list" id="sid-list">${buildList(entry.stock_ids)}</div>
       <div class="ean-add-row">
         <input id="sid-input" type="text" placeholder="${t('stock.stockid_placeholder')}" />
         <button type="button" class="btn btn-ghost btn-sm" id="btn-scan-sid" title="${t('stock.stockid_btn_scan')}">
           <i data-lucide="scan-barcode"></i>
         </button>
         <button type="button" class="btn btn-primary btn-sm" id="btn-add-sid">
           <i data-lucide="plus"></i> ${t('stock.stockid_btn_add')}
         </button>
       </div>
       <div id="sid-scanner-container" style="display:none;margin-top:12px">
         <div id="sid-reader"></div>
         <button type="button" class="btn btn-ghost btn-sm" id="btn-stop-sid-scan" style="margin-top:8px">
           <i data-lucide="x"></i> ${t('stock.stockid_btn_stop')}
         </button>
       </div>
     </div>
     <div class="form-actions" style="margin-top:16px">
       <button type="button" class="btn btn-ghost" id="sid-done">${t('stock.stockid_btn_done')}</button>
     </div>`
  );
  lucide.createIcons();

  const sidList  = overlay.querySelector('#sid-list');
  const sidInput = overlay.querySelector('#sid-input');
  let   ids      = [...entry.stock_ids];
  let   _scanner = null;

  const stopScanner = async () => {
    if (_scanner) {
      try { if (_scanner.isScanning) await _scanner.stop(); } catch (_) {}
      _scanner = null;
    }
    overlay.querySelector('#sid-scanner-container').style.display = 'none';
  };

  const refreshList = () => {
    sidList.innerHTML = buildList(ids);
    lucide.createIcons({ nodes: [sidList] });
    attachRemoveListeners();
  };

  const attachRemoveListeners = () => {
    sidList.querySelectorAll('[data-remove-sid]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const sid = Number(btn.dataset.removeSid);
        try {
          await removeStockId(entry.id, sid);
          ids = ids.filter(s => s.id !== sid);
          refreshList();
          showToast(t('stock.stockid_toast_removed'));
        } catch (err) {
          showToast(err.message, 'error');
        }
      });
    });
  };
  attachRemoveListeners();

  const addHandler = async () => {
    const code = sidInput.value.trim();
    if (!code) return;
    try {
      const newId = await addStockId(entry.id, code);
      ids.push(newId);
      sidInput.value = '';
      refreshList();
      showToast(t('stock.stockid_toast_added'));
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  overlay.querySelector('#btn-scan-sid').addEventListener('click', async () => {
    if (!window.Html5Qrcode) { showToast(t('common.scanner_unavailable'), 'error'); return; }
    const container = overlay.querySelector('#sid-scanner-container');
    container.style.display = 'block';
    _scanner = new Html5Qrcode('sid-reader');
    try {
      await _scanner.start(
        { facingMode: 'environment' },
        { fps: 10, qrbox: { width: 260, height: 260 } },
        async (decodedText) => {
          await stopScanner();
          sidInput.value = decodedText;
          sidInput.focus();
        },
        () => {}
      );
    } catch (_) {
      showToast(t('common.camera_unavailable'), 'error');
      _scanner = null;
      overlay.querySelector('#sid-scanner-container').style.display = 'none';
    }
  });

  overlay.querySelector('#btn-stop-sid-scan').addEventListener('click', stopScanner);
  overlay.querySelector('.modal-close').addEventListener('click', () => stopScanner());
  overlay.addEventListener('click', e => { if (e.target === overlay) stopScanner(); });

  overlay.querySelector('#btn-add-sid').addEventListener('click', addHandler);
  sidInput.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); addHandler(); } });
  overlay.querySelector('#sid-done').addEventListener('click', async () => { await stopScanner(); close(); render(); });
  sidInput.focus();
}

function showEntryModal(entry, products, vaults) {
  const isEdit = !!entry;

  const productOpts = products.map(p =>
    `<option value="${p.id}" ${isEdit && entry.product_id === p.id ? 'selected' : ''}>
       ${escHtml(p.vendor)} – ${escHtml(p.name)} (${escHtml(p.size)})
     </option>`
  ).join('');

  const vaultOpts = vaults.map(v =>
    `<option value="${v.id}" ${isEdit && entry.vault_id === v.id ? 'selected' : ''}>
       ${escHtml(v.description)}
     </option>`
  ).join('');

  const tagsSection = isEdit ? buildTagsSection(entry.tags) : '';

  const { overlay, close } = openModal(
    isEdit ? t('stock.modal_edit') : t('stock.modal_add'),
    `<form id="entry-form">
       <div class="form-field">
         <label for="ef-product">${t('stock.label_product')}</label>
         <select id="ef-product" name="product_id" required ${isEdit ? 'disabled' : ''}>
           <option value="">${t('stock.select_product')}</option>
           ${productOpts}
         </select>
       </div>
       <div class="form-field">
         <label for="ef-vault">${t('stock.label_vault')}</label>
         <select id="ef-vault" name="vault_id" required ${isEdit ? 'disabled' : ''}>
           <option value="">${t('stock.select_vault')}</option>
           ${vaultOpts}
         </select>
       </div>
       <div class="form-row">
         <div class="form-field">
           <label for="ef-qty">${t('stock.label_qty')}</label>
           <input id="ef-qty" name="quantity" type="number" min="0.01" step="0.01" required
             value="${isEdit ? entry.quantity : '1'}" />
         </div>
         <div class="form-field">
           <label for="ef-bbd">${t('stock.label_bbd')}</label>
           <input id="ef-bbd" name="best_before_date" type="date"
             value="${isEdit && entry.best_before_date ? entry.best_before_date : ''}" />
         </div>
       </div>
       <div class="form-field">
         <label for="ef-comment">${t('stock.label_comment')}</label>
         <input id="ef-comment" name="comment" type="text" placeholder="${t('stock.placeholder_comment')}"
           value="${isEdit ? escHtml(entry.comment ?? '') : ''}" />
       </div>
       ${tagsSection}
       <div class="form-actions">
         <button type="button" class="btn btn-ghost" id="ef-cancel">${t('common.cancel')}</button>
         <button type="submit" class="btn btn-primary">${isEdit ? t('common.save') : t('common.add')}</button>
       </div>
     </form>`
  );
  lucide.createIcons();

  if (isEdit) {
    attachTagListeners(overlay, entry.tags, entry.id, addTagToStockEntry, removeTagFromStockEntry, _allTags);
  }

  overlay.querySelector('#ef-cancel').addEventListener('click', close);
  overlay.querySelector('#entry-form').addEventListener('submit', async e => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      if (isEdit) {
        const data = {};
        const qty = parseFloat(fd.get('quantity'));
        if (!isNaN(qty)) data.quantity = qty;
        const bbd = fd.get('best_before_date');
        data.best_before_date = bbd || null;
        data.comment = fd.get('comment') || null;
        await updateStockEntry(entry.id, data);
        showToast(t('stock.toast_updated'));
      } else {
        const data = {
          product_id: Number(fd.get('product_id')),
          vault_id:   Number(fd.get('vault_id')),
          quantity:   parseFloat(fd.get('quantity')),
          best_before_date: fd.get('best_before_date') || null,
          comment: fd.get('comment') || null,
        };
        await createStockEntry(data);
        showToast(t('stock.toast_added'));
      }
      close();
      render();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}
