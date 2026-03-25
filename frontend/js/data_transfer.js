import { t } from './i18n.js';
import { showToast, escHtml } from './app.js';

export async function render() {
  const content = document.getElementById('app-content');

  // ── Fetch available export models ─────────────────────────────────────────
  let models = [];
  try {
    const res = await fetch('/api/export/models');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    models = await res.json();
  } catch (err) {
    content.innerHTML = `
      <div class="empty-state">
        <i data-lucide="circle-alert"></i>
        <p>${escHtml(err.message)}</p>
      </div>`;
    lucide.createIcons();
    return;
  }

  content.innerHTML = `
    <div class="page-header">
      <h1 class="page-title">${t('data_transfer.title')}</h1>
    </div>

    <!-- ── Export ── -->
    <div class="section-heading">${t('data_transfer.export_title')}</div>
    <p class="text-muted text-sm" style="margin-bottom:16px">${t('data_transfer.export_desc')}</p>

    <div class="export-card" style="max-width:560px">
      <label class="export-model-row export-model-row--header">
        <input type="checkbox" id="chk-select-all" />
        <span class="export-model-name">${t('data_transfer.select_all')}</span>
      </label>
      <div class="export-model-divider"></div>
      <div id="model-list">
        ${models.map(m => `
          <label class="export-model-row">
            <input type="checkbox" name="export-model" value="${escHtml(m.table_name)}" />
            <span class="export-model-name">${escHtml(m.display_name)}</span>
            <span class="badge badge-gray">${m.row_count}</span>
          </label>
        `).join('')}
      </div>
        <div class="export-actions">
        <button class="btn btn-primary" id="btn-export">
          <i data-lucide="download"></i>
          ${t('data_transfer.btn_export')}
        </button>
        <span id="export-status" class="text-muted text-sm"></span>
      </div>
    </div>
    <p class="text-muted text-sm" style="margin-top:8px;max-width:560px">
      <i data-lucide="image" style="width:13px;height:13px;vertical-align:-2px"></i>
      ${t('data_transfer.export_images_hint')}
    </p>

    <!-- ── Import ── -->
    <div class="section-heading" style="margin-top:40px">${t('data_transfer.import_title')}</div>
    <p class="text-muted text-sm" style="margin-bottom:16px">${t('data_transfer.import_desc')}</p>

    <div style="max-width:560px">
      <div class="import-drop-zone" id="import-drop-zone">
        <input type="file" id="import-file" accept=".zip" style="display:none" />
        <i data-lucide="file-archive"></i>
        <span id="import-drop-label">${t('data_transfer.import_drop_label')}</span>
        <span class="text-muted text-sm" id="import-filename"></span>
      </div>

      <div style="margin-top:12px;display:flex;gap:12px;align-items:center">
        <button class="btn btn-ghost" id="btn-preview" disabled>
          <i data-lucide="eye"></i>
          ${t('data_transfer.btn_preview')}
        </button>
        <span id="import-status" class="text-muted text-sm"></span>
      </div>

      <!-- Preview table (hidden until loaded) -->
      <div id="import-preview" style="display:none;margin-top:20px">
        <div class="table-container">
          <div class="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>${t('data_transfer.col_model')}</th>
                  <th>${t('data_transfer.col_rows')}</th>
                  <th>${t('data_transfer.col_status')}</th>
                </tr>
              </thead>
              <tbody id="preview-tbody"></tbody>
            </table>
          </div>
        </div>
        <div style="margin-top:16px;display:flex;gap:12px;align-items:center">
          <button class="btn btn-primary" id="btn-import">
            <i data-lucide="upload"></i>
            ${t('data_transfer.btn_import')}
          </button>
          <span id="apply-status" class="text-muted text-sm"></span>
        </div>
      </div>

      <!-- Result table (hidden until import done) -->
      <div id="import-result" style="display:none;margin-top:20px">
        <div class="table-container">
          <div class="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>${t('data_transfer.col_model')}</th>
                  <th>${t('data_transfer.col_imported')}</th>
                  <th>${t('data_transfer.col_total')}</th>
                  <th>${t('data_transfer.col_status')}</th>
                </tr>
              </thead>
              <tbody id="result-tbody"></tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  `;

  lucide.createIcons();

  // ── Export logic ──────────────────────────────────────────────────────────
  const selectAll   = content.querySelector('#chk-select-all');
  const checkboxes  = content.querySelectorAll('input[name="export-model"]');

  const syncSelectAll = () => {
    const n = Array.from(checkboxes).filter(c => c.checked).length;
    selectAll.checked = n === checkboxes.length;
    selectAll.indeterminate = n > 0 && n < checkboxes.length;
  };

  selectAll.addEventListener('change', () => {
    checkboxes.forEach(cb => { cb.checked = selectAll.checked; });
  });
  checkboxes.forEach(cb => cb.addEventListener('change', syncSelectAll));

  content.querySelector('#btn-export').addEventListener('click', async () => {
    const selected = Array.from(checkboxes).filter(cb => cb.checked).map(cb => cb.value);
    if (selected.length === 0) {
      showToast(t('data_transfer.toast_nothing_selected'), 'error');
      return;
    }
    const btn = content.querySelector('#btn-export');
    const statusEl = content.querySelector('#export-status');
    btn.disabled = true;
    statusEl.textContent = t('data_transfer.exporting');
    try {
      const res = await fetch('/api/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tables: selected }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href     = url;
      a.download = `homeerp_export_${new Date().toISOString().slice(0, 10)}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      showToast(t('data_transfer.toast_exported'));
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      btn.disabled = false;
      statusEl.textContent = '';
    }
  });

  // ── Import logic ──────────────────────────────────────────────────────────
  const dropZone      = content.querySelector('#import-drop-zone');
  const fileInput     = content.querySelector('#import-file');
  const filenameEl    = content.querySelector('#import-filename');
  const btnPreview    = content.querySelector('#btn-preview');
  const importStatus  = content.querySelector('#import-status');
  const previewPanel  = content.querySelector('#import-preview');
  const resultPanel   = content.querySelector('#import-result');
  const btnImport     = content.querySelector('#btn-import');
  const applyStatus   = content.querySelector('#apply-status');

  let currentImportId = null;

  const setFile = (file) => {
    if (!file) return;
    fileInput._selectedFile = file;
    filenameEl.textContent  = file.name;
    btnPreview.disabled     = false;
    previewPanel.style.display  = 'none';
    resultPanel.style.display   = 'none';
    currentImportId = null;
  };

  dropZone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', () => setFile(fileInput.files[0]));

  dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    setFile(e.dataTransfer.files[0]);
  });

  btnPreview.addEventListener('click', async () => {
    const file = fileInput._selectedFile;
    if (!file) return;

    btnPreview.disabled    = true;
    importStatus.textContent = t('data_transfer.loading_preview');
    previewPanel.style.display = 'none';
    resultPanel.style.display  = 'none';
    currentImportId = null;

    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch('/api/import/preview', { method: 'POST', body: fd });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        throw new Error(err.detail ?? `HTTP ${res.status}`);
      }
      const data = await res.json();
      currentImportId = data.import_id;

      const tbody = content.querySelector('#preview-tbody');
      tbody.innerHTML = data.preview.map(row => {
        const isImages = row.table_name === '__images__';
        const badge = row.known
          ? `<span class="badge badge-green">${t('data_transfer.status_known')}</span>`
          : `<span class="badge badge-gray">${t('data_transfer.status_unknown')}</span>`;
        const icon = isImages ? `<i data-lucide="image" style="width:14px;height:14px;vertical-align:-2px;margin-right:4px"></i>` : '';
        const label = isImages ? t('data_transfer.images_label') : escHtml(row.display_name);
        return `<tr>
          <td>${icon}${label}</td>
          <td>${row.row_count}</td>
          <td>${badge}</td>
        </tr>`;
      }).join('');
      lucide.createIcons({ nodes: [tbody] });

      previewPanel.style.display = '';
      btnImport.disabled = data.preview.every(r => !r.known);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      btnPreview.disabled      = false;
      importStatus.textContent = '';
    }
  });

  btnImport.addEventListener('click', async () => {
    if (!currentImportId) return;

    btnImport.disabled    = true;
    applyStatus.textContent = t('data_transfer.importing');

    try {
      const res = await fetch(`/api/import/apply/${currentImportId}`, { method: 'POST' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        throw new Error(err.detail ?? `HTTP ${res.status}`);
      }
      const data = await res.json();

      const hasErrors = data.results.some(r => r.error);
      const tbody = content.querySelector('#result-tbody');
      tbody.innerHTML = data.results.map(row => {
        const isImages = row.table_name === '__images__';
        let statusCell;
        if (row.error === 'unknown_table') {
          statusCell = `<span class="badge badge-gray">${t('data_transfer.status_skipped')}</span>`;
        } else if (row.error) {
          statusCell = `<span class="badge badge-red" title="${escHtml(row.error)}">${t('data_transfer.status_error')}</span>`;
        } else {
          statusCell = `<span class="badge badge-green">${t('data_transfer.status_ok')}</span>`;
        }
        const icon  = isImages ? `<i data-lucide="image" style="width:14px;height:14px;vertical-align:-2px;margin-right:4px"></i>` : '';
        const label = isImages ? t('data_transfer.images_label') : escHtml(row.display_name);
        return `<tr>
          <td>${icon}${label}</td>
          <td>${row.imported}</td>
          <td>${row.total}</td>
          <td>${statusCell}</td>
        </tr>`;
      }).join('');
      lucide.createIcons({ nodes: [tbody] });

      previewPanel.style.display = 'none';
      resultPanel.style.display  = '';
      currentImportId = null;

      showToast(
        hasErrors ? t('data_transfer.toast_import_with_errors') : t('data_transfer.toast_import_done'),
        hasErrors ? 'error' : 'success',
      );
    } catch (err) {
      showToast(err.message, 'error');
      btnImport.disabled = false;
    } finally {
      applyStatus.textContent = '';
    }
  });
}
