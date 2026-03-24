import { getCategories, createCategory, updateCategory, deleteCategory, getUnits } from './api.js';
import { openModal, openConfirm, showToast, escHtml, fmtQty, buildUnitOptions } from './app.js';
import { t } from './i18n.js';

let _allUnits = [];

export async function render() {
  const content = document.getElementById('app-content');
  const [categories, units] = await Promise.all([getCategories(), getUnits()]);
  _allUnits = units;

  const rows = categories.map(c => {
    const minStock = c.min_stock_quantity != null
      ? `${fmtQty(c.min_stock_quantity)}${c.min_stock_unit ? ' ' + escHtml(c.min_stock_unit.abbreviation) : ''}`
      : '<span class="text-muted">—</span>';
    return `
      <tr>
        <td class="font-semibold">${escHtml(c.name)}</td>
        <td>${minStock}</td>
        <td>
          <div class="td-actions">
            <button class="btn btn-ghost btn-sm" data-edit="${c.id}">
              <i data-lucide="pencil"></i> ${t('categories.btn_edit')}
            </button>
            <button class="btn btn-danger btn-sm" data-delete="${c.id}" data-name="${escHtml(c.name)}">
              <i data-lucide="trash-2"></i>
            </button>
          </div>
        </td>
      </tr>`;
  }).join('');

  const emptyRow = `
    <tr><td colspan="3">
      <div class="empty-state"><i data-lucide="tag"></i><p>${t('categories.empty')}</p></div>
    </td></tr>`;

  content.innerHTML = `
    <div class="page-header">
      <h1 class="page-title">${t('categories.title')}</h1>
      <div class="page-header-actions">
        <button class="btn btn-primary" id="btn-add-category">
          <i data-lucide="plus"></i> ${t('categories.btn_add')}
        </button>
      </div>
    </div>
    <div class="table-container">
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>${t('categories.col_name')}</th>
              <th>${t('categories.col_min_stock')}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>${rows || emptyRow}</tbody>
        </table>
      </div>
    </div>`;

  document.getElementById('btn-add-category').addEventListener('click', () => showCategoryModal(null));

  content.querySelectorAll('[data-edit]').forEach(btn => {
    const cat = categories.find(c => c.id === Number(btn.dataset.edit));
    btn.addEventListener('click', () => cat && showCategoryModal(cat));
  });

  content.querySelectorAll('[data-delete]').forEach(btn => {
    const id   = Number(btn.dataset.delete);
    const name = btn.dataset.name;
    btn.addEventListener('click', () => {
      openConfirm(t('categories.confirm_delete', { name }), async () => {
        try {
          await deleteCategory(id);
          showToast(t('categories.toast_deleted'));
          render();
        } catch (err) {
          showToast(err.message, 'error');
        }
      });
    });
  });
}

function showCategoryModal(category) {
  const isEdit = !!category;

  const { overlay, close } = openModal(
    isEdit ? t('categories.modal_edit') : t('categories.modal_add'),
    `<form id="cat-form">
       <div class="form-field">
         <label for="cf-name">${t('categories.label_name')}</label>
         <input id="cf-name" name="name" type="text" required placeholder="${t('categories.placeholder_name')}"
           value="${isEdit ? escHtml(category.name) : ''}" />
       </div>
       <div class="form-row">
         <div class="form-field">
           <label for="cf-qty">${t('categories.label_min_qty')}</label>
           <input id="cf-qty" name="min_stock_quantity" type="number" min="0" step="any"
             placeholder="${t('categories.placeholder_min_qty')}"
             value="${isEdit && category.min_stock_quantity != null ? category.min_stock_quantity : ''}" />
         </div>
         <div class="form-field">
           <label for="cf-unit">${t('categories.label_unit')}</label>
           <select id="cf-unit" name="min_stock_unit_id">
             ${buildUnitOptions(_allUnits, isEdit ? category.min_stock_unit_id : null, { nullable: true, placeholder: t('common.no_category') })}
           </select>
         </div>
       </div>
       <div class="form-actions">
         <button type="button" class="btn btn-ghost" id="cf-cancel">${t('common.cancel')}</button>
         <button type="submit" class="btn btn-primary">${isEdit ? t('common.save') : t('common.create')}</button>
       </div>
     </form>`
  );
  lucide.createIcons();

  overlay.querySelector('#cf-cancel').addEventListener('click', close);
  overlay.querySelector('#cat-form').addEventListener('submit', async e => {
    e.preventDefault();
    const fd  = new FormData(e.target);
    const qty = fd.get('min_stock_quantity');
    const uid = fd.get('min_stock_unit_id');
    const data = {
      name: fd.get('name'),
      min_stock_quantity: qty ? Number(qty) : null,
      min_stock_unit_id:  uid ? Number(uid) : null,
    };
    try {
      if (isEdit) {
        await updateCategory(category.id, data);
        showToast(t('categories.toast_saved'));
      } else {
        await createCategory(data);
        showToast(t('categories.toast_created'));
      }
      close();
      render();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  overlay.querySelector('#cf-name').focus();
}
