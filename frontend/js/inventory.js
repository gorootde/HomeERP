import { getVaults, getStockEntries, getByEan, updateStockEntry, createStockEntry, deleteStockEntry } from './api.js';
import { showToast, escHtml, fmtQty } from './app.js';
import { t } from './i18n.js';

let _scanner  = null;
let _session  = null;

export async function render() {
  const content = document.getElementById('app-content');
  _session = null;

  const vaults = await getVaults();

  const vaultOpts = vaults.map(v =>
    `<option value="${v.id}">${escHtml(v.description)}</option>`
  ).join('');

  content.innerHTML = `
    <div class="page-header"><h1 class="page-title">${t('inventory.title')}</h1></div>
    <div class="inventory-steps">
      <div class="step-card" id="step-select">
        <h2 style="font-size:1rem;font-weight:700;margin-bottom:12px">
          <i data-lucide="warehouse" style="display:inline-block;width:18px;height:18px;vertical-align:middle;margin-right:6px"></i>
          ${t('inventory.step_select_heading')}
        </h2>
        <div class="form-field">
          <label for="inv-vault-select">${t('inventory.label_vault')}</label>
          <select id="inv-vault-select">
            <option value="">${t('inventory.select_vault')}</option>
            ${vaultOpts}
          </select>
        </div>
        <button class="btn btn-primary" id="btn-start-inv" disabled>
          <i data-lucide="play"></i> ${t('inventory.btn_start')}
        </button>
      </div>
    </div>`;

  lucide.createIcons();

  const vaultSelect = document.getElementById('inv-vault-select');
  const startBtn    = document.getElementById('btn-start-inv');

  vaultSelect.addEventListener('change', () => {
    startBtn.disabled = !vaultSelect.value;
  });

  startBtn.addEventListener('click', async () => {
    const vaultId = Number(vaultSelect.value);
    const vault   = vaults.find(v => v.id === vaultId);
    await startSession(vault);
  });
}

async function startSession(vault) {
  const content = document.getElementById('app-content');

  // Build expected map from current DB state
  const entries  = await getStockEntries({ vault_id: vault.id, limit: 500 });
  const expected = new Map();
  for (const e of entries) {
    const prev = expected.get(e.product_id) ?? { product: e.product, totalQty: 0, entries: [] };
    prev.totalQty += e.quantity;
    prev.entries.push(e);
    expected.set(e.product_id, prev);
  }

  _session = {
    vault,
    expected,
    scanned: new Map(),   // productId → { product, count }
    unknown: [],          // EANs not in DB
  };

  renderScanStep(content);
}

function renderScanStep(content) {
  const s = _session;
  content.innerHTML = `
    <div class="page-header">
      <h1 class="page-title">${t('inventory.counting_title', { vault: escHtml(s.vault.description) })}</h1>
    </div>
    <div class="inventory-steps">
      <div class="step-card">
        <div class="tally-counter" id="tally-counter">
          <div class="tally-item">
            <div class="num" id="tally-scans">0</div>
            <div class="lbl">${t('inventory.tally_scans')}</div>
          </div>
          <div class="tally-item">
            <div class="num" id="tally-products">0</div>
            <div class="lbl">${t('inventory.tally_products')}</div>
          </div>
          <div class="tally-item">
            <div class="num" id="tally-expected">${s.expected.size}</div>
            <div class="lbl">${t('inventory.tally_expected')}</div>
          </div>
        </div>

        <div id="inv-qr-reader" style="margin:16px 0"></div>

        <div id="inv-scan-feedback" class="text-muted text-sm" style="text-align:center;margin-bottom:12px">
          ${t('inventory.feedback_initial')}
        </div>

        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button class="btn btn-primary" id="btn-toggle-scanner">
            <i data-lucide="scan"></i> ${t('inventory.btn_start_scanner')}
          </button>
          <button class="btn btn-primary" id="btn-finish-inv">
            <i data-lucide="clipboard-check"></i> ${t('inventory.btn_finish')}
          </button>
          <button class="btn btn-ghost" id="btn-cancel-inv">
            <i data-lucide="x"></i> ${t('inventory.btn_cancel')}
          </button>
        </div>
      </div>
    </div>`;

  lucide.createIcons();

  const toggleBtn = document.getElementById('btn-toggle-scanner');
  toggleBtn.addEventListener('click', async () => {
    const feedback = document.getElementById('inv-scan-feedback');
    if (_scanner) {
      await stopScannerForInventory();
      toggleBtn.innerHTML = `<i data-lucide="scan"></i> ${t('inventory.btn_start_scanner')}`;
      toggleBtn.className = 'btn btn-primary';
      if (feedback) feedback.textContent = t('inventory.feedback_stopped');
    } else {
      toggleBtn.disabled = true;
      await startScannerForInventory();
      toggleBtn.disabled = false;
      if (_scanner) {
        toggleBtn.innerHTML = `<i data-lucide="scan-off"></i> ${t('inventory.btn_stop_scanner')}`;
        toggleBtn.className = 'btn btn-ghost';
        if (feedback) feedback.textContent = t('inventory.feedback_scanning');
      } else {
        if (feedback) feedback.textContent = t('inventory.feedback_camera_unavailable');
      }
    }
    lucide.createIcons({ nodes: [toggleBtn] });
  });

  document.getElementById('btn-finish-inv').addEventListener('click', () => {
    stopScannerForInventory();
    showComparison();
  });

  document.getElementById('btn-cancel-inv').addEventListener('click', () => {
    stopScannerForInventory();
    render();
  });
}

async function startScannerForInventory() {
  if (!window.Html5Qrcode) return;

  _scanner = new Html5Qrcode('inv-qr-reader');
  try {
    await _scanner.start(
      { facingMode: 'environment' },
      { fps: 10, qrbox: { width: 280, height: 140 } },
      onInventoryScan,
      () => {}
    );
  } catch (_) {
    const fb = document.getElementById('inv-scan-feedback');
    if (fb) fb.textContent = t('inventory.feedback_camera_fallback');
    _scanner = null;
  }
}

async function onInventoryScan(decodedText) {
  const feedback = document.getElementById('inv-scan-feedback');

  try {
    const product = await getByEan(decodedText);
    const pid     = product.id;

    const prev = _session.scanned.get(pid) ?? { product, count: 0 };
    prev.count += 1;
    _session.scanned.set(pid, prev);

    if (feedback) feedback.innerHTML =
      `<span style="color:var(--color-success)">✓ ${escHtml(product.name)}</span>${t('inventory.feedback_scanned', { count: prev.count })}`;

  } catch (err) {
    if (err.status === 404) {
      if (!_session.unknown.includes(decodedText)) {
        _session.unknown.push(decodedText);
      }
      if (feedback) feedback.innerHTML =
        `<span style="color:var(--color-warning)">${t('inventory.feedback_unknown_ean', { ean: escHtml(decodedText) })}</span>`;
    }
  }

  updateTally();
}

function updateTally() {
  const s = _session;
  const totalScans = [...s.scanned.values()].reduce((sum, v) => sum + v.count, 0);
  const el = id => document.getElementById(id);
  if (el('tally-scans'))    el('tally-scans').textContent    = totalScans;
  if (el('tally-products')) el('tally-products').textContent = s.scanned.size;
}

async function stopScannerForInventory() {
  if (_scanner) {
    try { if (_scanner.isScanning) await _scanner.stop(); } catch (_) {}
    _scanner = null;
  }
}

function showComparison() {
  const s = _session;
  const content = document.getElementById('app-content');

  const results = [];

  // Check all expected products
  for (const [pid, { product, totalQty, entries }] of s.expected) {
    const scannedQty = s.scanned.get(pid)?.count ?? 0;
    const diff = scannedQty - totalQty;
    const status = diff === 0 ? 'ok' : diff < 0 ? 'missing' : 'extra';
    results.push({ status, product, expected: totalQty, scanned: scannedQty, diff, dbEntries: entries });
  }

  // Products scanned but not expected (not in DB for this vault)
  for (const [pid, { product, count }] of s.scanned) {
    if (!s.expected.has(pid)) {
      results.push({ status: 'unexpected', product, expected: 0, scanned: count, diff: count, dbEntries: [] });
    }
  }

  // Sort: problems first
  const order = { missing: 0, extra: 1, unexpected: 2, ok: 3 };
  results.sort((a, b) => order[a.status] - order[b.status]);

  const counts = { ok: 0, missing: 0, extra: 0, unexpected: 0 };
  for (const r of results) counts[r.status]++;

  const statusBadge = s => ({
    ok:         `<span class="badge badge-green">${t('inventory.status_ok')}</span>`,
    missing:    `<span class="badge badge-red">${t('inventory.status_missing')}</span>`,
    extra:      `<span class="badge badge-orange">${t('inventory.status_extra')}</span>`,
    unexpected: `<span class="badge badge-blue">${t('inventory.status_unexpected')}</span>`,
  }[s]);

  const rowClass = s => ({ ok: 'row-ok', missing: 'row-missing', extra: 'row-extra', unexpected: 'row-unexpected' }[s]);

  const rows = results.map((r, i) => `
    <tr class="${rowClass(r.status)}" data-idx="${i}">
      <td>
        <div class="font-semibold">${escHtml(r.product.name)}</div>
        <div class="text-muted text-sm">${escHtml(r.product.vendor)} · ${escHtml(r.product.size)}</div>
      </td>
      <td style="text-align:right">${fmtQty(r.expected)}</td>
      <td style="text-align:right">${fmtQty(r.scanned)}</td>
      <td style="text-align:right;font-weight:600">
        ${r.diff === 0 ? '—' : (r.diff > 0 ? '+' : '') + fmtQty(r.diff)}
      </td>
      <td>${statusBadge(r.status)}</td>
      <td>
        ${r.status !== 'ok'
          ? `<button class="btn btn-ghost btn-sm" data-correct="${i}">
               <i data-lucide="check"></i> ${t('inventory.btn_update_db')}
             </button>`
          : ''}
      </td>
    </tr>`).join('');

  const emptyRow = `<tr><td colspan="6"><div class="empty-state"><i data-lucide="check-circle-2"></i><p>${t('inventory.empty')}</p></div></td></tr>`;

  const hasProblems = results.some(r => r.status !== 'ok');

  content.innerHTML = `
    <div class="page-header">
      <h1 class="page-title">${t('inventory.result_title', { vault: escHtml(s.vault.description) })}</h1>
    </div>
    <div class="result-summary">
      ${counts.ok         ? `<span class="badge badge-green">${counts.ok} ${t('inventory.status_ok')}</span>` : ''}
      ${counts.missing    ? `<span class="badge badge-red">${counts.missing} ${t('inventory.status_missing')}</span>` : ''}
      ${counts.extra      ? `<span class="badge badge-orange">${counts.extra} ${t('inventory.status_extra')}</span>` : ''}
      ${counts.unexpected ? `<span class="badge badge-blue">${counts.unexpected} ${t('inventory.status_unexpected')}</span>` : ''}
    </div>
    ${s.unknown.length ? `<div style="margin-bottom:12px" class="text-sm text-muted">${t('inventory.unknown_eans_prefix')} ${s.unknown.map(e => `<span class="font-mono badge badge-gray">${escHtml(e)}</span>`).join(' ')}</div>` : ''}

    <div class="table-container" style="margin-bottom:16px">
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>${t('inventory.col_product')}</th>
              <th style="text-align:right">${t('inventory.col_expected')}</th>
              <th style="text-align:right">${t('inventory.col_scanned')}</th>
              <th style="text-align:right">${t('inventory.col_diff')}</th>
              <th>${t('inventory.col_status')}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>${rows || emptyRow}</tbody>
        </table>
      </div>
    </div>

    <div style="display:flex;gap:8px;flex-wrap:wrap">
      ${hasProblems ? `<button class="btn btn-primary" id="btn-apply-all"><i data-lucide="check-check"></i> ${t('inventory.btn_apply_all')}</button>` : ''}
      <button class="btn btn-ghost" id="btn-new-inv"><i data-lucide="rotate-ccw"></i> ${t('inventory.btn_new')}</button>
    </div>`;

  lucide.createIcons();

  // Per-row corrections
  content.querySelectorAll('[data-correct]').forEach(btn => {
    const idx = Number(btn.dataset.correct);
    btn.addEventListener('click', async () => {
      await applyCorrection(results[idx], s.vault.id);
      btn.closest('tr').querySelectorAll('td').forEach((td, i) => {
        if (i === 4) td.innerHTML = statusBadge('ok');
        if (i === 5) td.innerHTML = '';
      });
      btn.closest('tr').className = rowClass('ok');
      results[idx].status = 'ok';
    });
  });

  // Apply all
  document.getElementById('btn-apply-all')?.addEventListener('click', async () => {
    const toFix = results.filter(r => r.status !== 'ok');
    for (const r of toFix) {
      await applyCorrection(r, s.vault.id);
    }
    showToast(t('inventory.toast_applied', { n: toFix.length }));
    render();
  });

  document.getElementById('btn-new-inv').addEventListener('click', render);
}

async function applyCorrection(result, vaultId) {
  const { status, product, scanned, dbEntries } = result;
  try {
    if (status === 'missing' || status === 'extra') {
      // Update first entry to scanned qty, delete rest
      if (dbEntries.length > 0) {
        if (scanned === 0) {
          for (const e of dbEntries) await deleteStockEntry(e.id);
        } else {
          await updateStockEntry(dbEntries[0].id, { quantity: scanned });
          for (const e of dbEntries.slice(1)) await deleteStockEntry(e.id);
        }
      }
    } else if (status === 'unexpected') {
      await createStockEntry({
        product_id: product.id,
        vault_id: vaultId,
        quantity: scanned,
      });
    }
    showToast(t('inventory.toast_updated', { name: product.name }));
  } catch (err) {
    showToast(err.message, 'error');
  }
}

export async function cleanup() {
  await stopScannerForInventory();
}
