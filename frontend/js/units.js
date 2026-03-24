import { getUnits, createUnit, updateUnit, deleteUnit, addConversion, deleteConversion } from './api.js';
import { openModal, openConfirm, showToast, escHtml, fmtFactor } from './app.js';
import { t } from './i18n.js';

export async function render() {
  const content = document.getElementById('app-content');
  const units = await getUnits();

  const rows = units.map(u => `
    <tr>
      <td class="text-muted font-mono" style="width:60px">${u.id}</td>
      <td>${escHtml(u.name)}</td>
      <td><span class="badge">${escHtml(u.abbreviation)}</span></td>
      <td class="text-muted text-sm">${u.conversions.length} ${u.conversions.length !== 1 ? t('units.conv_count_plural') : t('units.conv_count_singular')}</td>
      <td>
        <div class="td-actions">
          <button class="btn btn-ghost btn-sm" data-edit="${u.id}">
            <i data-lucide="pencil"></i> ${t('units.btn_edit')}
          </button>
          <button class="btn btn-danger btn-sm" data-delete="${u.id}" data-name="${escHtml(u.name)}">
            <i data-lucide="trash-2"></i>
          </button>
        </div>
      </td>
    </tr>`).join('');

  const emptyRow = `
    <tr><td colspan="5">
      <div class="empty-state"><i data-lucide="ruler"></i><p>${t('units.empty')}</p></div>
    </td></tr>`;

  content.innerHTML = `
    <div class="page-header">
      <h1 class="page-title">${t('units.title')}</h1>
      <div class="page-header-actions">
        <button class="btn btn-primary" id="btn-add-unit">
          <i data-lucide="plus"></i> ${t('units.btn_add')}
        </button>
      </div>
    </div>
    <div class="table-container">
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th style="width:60px">${t('units.col_id')}</th>
              <th>${t('units.col_name')}</th>
              <th>${t('units.col_abbr')}</th>
              <th>${t('units.col_conversions')}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>${rows || emptyRow}</tbody>
        </table>
      </div>
    </div>`;

  document.getElementById('btn-add-unit').addEventListener('click', () => showUnitModal(null, units));

  content.querySelectorAll('[data-edit]').forEach(btn => {
    const unit = units.find(u => u.id === Number(btn.dataset.edit));
    btn.addEventListener('click', () => showUnitModal(unit, units));
  });

  content.querySelectorAll('[data-delete]').forEach(btn => {
    const id   = Number(btn.dataset.delete);
    const name = btn.dataset.name;
    btn.addEventListener('click', () => {
      openConfirm(t('units.confirm_delete', { name }), async () => {
        try {
          await deleteUnit(id);
          showToast(t('units.toast_deleted'));
          render();
        } catch (err) {
          showToast(err.message, 'error');
        }
      });
    });
  });
}

function renderConversionRows(conversions) {
  if (!conversions || conversions.length === 0) {
    return `<p class="text-muted text-sm" id="conv-empty">${t('units.conv_empty')}</p>`;
  }
  return `<table class="conv-table" id="conv-table">
    <thead><tr><th>${t('units.conv_col_factor')}</th><th>${t('units.conv_col_target')}</th><th></th></tr></thead>
    <tbody>
      ${conversions.map(c => `
        <tr data-conv-id="${c.id}">
          <td>1 <span class="abbr-placeholder"></span> = ${fmtFactor(c.factor)} <strong>${escHtml(c.to_unit.abbreviation)}</strong></td>
          <td class="text-muted text-sm">${escHtml(c.to_unit.name)}</td>
          <td>
            <button type="button" class="btn btn-danger btn-sm btn-delete-conv" data-conv-id="${c.id}">
              <i data-lucide="trash-2"></i>
            </button>
          </td>
        </tr>`).join('')}
    </tbody>
  </table>`;
}

function showUnitModal(unit, allUnits) {
  const isEdit = !!unit;
  let conversions = isEdit ? [...unit.conversions] : [];

  const otherUnits = allUnits.filter(u => !unit || u.id !== unit.id);
  const unitOptions = otherUnits.map(u =>
    `<option value="${u.id}">${escHtml(u.name)} (${escHtml(u.abbreviation)})</option>`
  ).join('');

  const { overlay, close } = openModal(
    isEdit ? t('units.modal_edit') : t('units.modal_add'),
    `<form id="unit-form">
       <div class="form-field">
         <label for="uf-name">${t('units.label_name')}</label>
         <input id="uf-name" name="name" type="text" required placeholder="${t('units.placeholder_name')}"
           value="${isEdit ? escHtml(unit.name) : ''}" />
       </div>
       <div class="form-field">
         <label for="uf-abbr">${t('units.label_abbr')}</label>
         <input id="uf-abbr" name="abbreviation" type="text" required placeholder="${t('units.placeholder_abbr')}"
           value="${isEdit ? escHtml(unit.abbreviation) : ''}" />
       </div>
       ${isEdit ? `
       <div class="form-field">
         <label>${t('units.label_conversions')}</label>
         <div id="conv-list">${renderConversionRows(conversions)}</div>
         ${otherUnits.length > 0 ? `
         <div class="ean-add-row" style="margin-top:0.5rem">
           <input id="uf-factor" type="number" step="any" min="0.000001" placeholder="${t('units.conv_placeholder_factor')}" style="width:100px" />
           <select id="uf-to-unit" style="flex:1">${unitOptions}</select>
           <button type="button" class="btn btn-ghost btn-sm" id="btn-add-conv">
             <i data-lucide="plus"></i> ${t('units.conv_btn_add')}
           </button>
         </div>
         <p id="conv-preview" class="text-muted text-sm conv-preview"></p>` : `<p class="text-muted text-sm" style="margin-top:0.5rem">${t('units.conv_no_other_units')}</p>`}
       </div>` : ''}
       <div class="form-actions">
         <button type="button" class="btn btn-ghost" id="uf-cancel">${t('common.cancel')}</button>
         <button type="submit" class="btn btn-primary">${isEdit ? t('common.save') : t('common.create')}</button>
       </div>
     </form>`,
    { wide: isEdit }
  );

  // Update abbreviation placeholders in conversion table
  const updateAbbr = () => {
    const abbr = overlay.querySelector('#uf-abbr')?.value.trim() || (isEdit ? unit.abbreviation : '?');
    overlay.querySelectorAll('.abbr-placeholder').forEach(el => { el.textContent = abbr; });
  };
  const updatePreview = () => {
    const preview = overlay.querySelector('#conv-preview');
    if (!preview) return;
    const abbr    = overlay.querySelector('#uf-abbr')?.value.trim() || unit.abbreviation;
    const factor  = parseFloat(overlay.querySelector('#uf-factor')?.value);
    const sel     = overlay.querySelector('#uf-to-unit');
    const toAbbr  = sel?.options[sel.selectedIndex]?.text.match(/\(([^)]+)\)$/)?.[1] ?? '';
    if (abbr && factor > 0 && toAbbr) {
      preview.textContent = t('units.conv_preview', { abbr, factor: fmtFactor(factor), to_abbr: toAbbr });
    } else {
      preview.textContent = '';
    }
  };

  if (isEdit) {
    updateAbbr();
    overlay.querySelector('#uf-abbr')?.addEventListener('input', () => { updateAbbr(); updatePreview(); });
    overlay.querySelector('#uf-factor')?.addEventListener('input', updatePreview);
    overlay.querySelector('#uf-to-unit')?.addEventListener('change', updatePreview);
  }

  const refreshConvList = () => {
    const container = overlay.querySelector('#conv-list');
    if (!container) return;
    container.innerHTML = renderConversionRows(conversions);
    lucide.createIcons({ nodes: [container] });
    updateAbbr();
    attachConvDeleteListeners();
  };

  const attachConvDeleteListeners = () => {
    overlay.querySelectorAll('.btn-delete-conv').forEach(btn => {
      btn.addEventListener('click', async () => {
        const convId = Number(btn.dataset.convId);
        try {
          await deleteConversion(unit.id, convId);
          conversions = conversions.filter(c => c.id !== convId);
          refreshConvList();
          showToast(t('units.toast_conv_deleted'));
        } catch (err) {
          showToast(err.message, 'error');
        }
      });
    });
  };

  if (isEdit) {
    attachConvDeleteListeners();
    const btnAdd = overlay.querySelector('#btn-add-conv');
    if (btnAdd) {
      btnAdd.addEventListener('click', async () => {
        const factorInput = overlay.querySelector('#uf-factor');
        const toUnitSel   = overlay.querySelector('#uf-to-unit');
        const factor      = parseFloat(factorInput.value);
        const toUnitId    = Number(toUnitSel.value);
        if (!factor || factor <= 0) {
          showToast(t('units.toast_conv_err_factor'), 'error');
          return;
        }
        try {
          const newConv = await addConversion(unit.id, { to_unit_id: toUnitId, factor });
          conversions = conversions.filter(c => c.id !== newConv.id);
          conversions.push(newConv);
          factorInput.value = '';
          refreshConvList();
          showToast(t('units.toast_conv_saved'));
        } catch (err) {
          showToast(err.message, 'error');
        }
      });
    }
  }

  overlay.querySelector('#uf-cancel').addEventListener('click', close);
  overlay.querySelector('#unit-form').addEventListener('submit', async e => {
    e.preventDefault();
    const name         = overlay.querySelector('#uf-name').value.trim();
    const abbreviation = overlay.querySelector('#uf-abbr').value.trim();
    try {
      if (isEdit) {
        await updateUnit(unit.id, { name, abbreviation });
        showToast(t('units.toast_saved'));
      } else {
        await createUnit({ name, abbreviation });
        showToast(t('units.toast_created'));
      }
      close();
      render();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  overlay.querySelector('#uf-name').focus();
}
