import { getVaults, createVault, updateVault, deleteVault, getTags, addTagToVault, removeTagFromVault } from './api.js';
import { openModal, openConfirm, showToast, escHtml, renderTagChips, buildTagsSection, attachTagListeners } from './app.js';
import { t } from './i18n.js';

let _allTags = [];

export async function render() {
  const content = document.getElementById('app-content');
  const [vaults] = await Promise.all([getVaults(), getTags().then(t => { _allTags = t; })]);

  const rows = vaults.map(v => `
    <tr>
      <td class="text-muted font-mono" style="width:60px">${v.id}</td>
      <td>${escHtml(v.description)}</td>
      <td><div class="item-tags">${renderTagChips(v.tags)}</div></td>
      <td>
        <div class="td-actions">
          <button class="btn btn-ghost btn-sm" data-edit="${v.id}">
            <i data-lucide="pencil"></i> ${t('common.edit')}
          </button>
          <button class="btn btn-danger btn-sm" data-delete="${v.id}" data-desc="${escHtml(v.description)}">
            <i data-lucide="trash-2"></i>
          </button>
        </div>
      </td>
    </tr>`).join('');

  const emptyRow = `
    <tr><td colspan="4">
      <div class="empty-state"><i data-lucide="warehouse"></i><p>${t('vaults.empty')}</p></div>
    </td></tr>`;

  content.innerHTML = `
    <div class="page-header">
      <h1 class="page-title">${t('vaults.title')}</h1>
      <div class="page-header-actions">
        <button class="btn btn-primary" id="btn-add-vault">
          <i data-lucide="plus"></i> ${t('vaults.btn_add')}
        </button>
      </div>
    </div>
    <div class="table-container">
      <div class="table-scroll">
        <table>
          <thead><tr><th style="width:60px">${t('vaults.col_id')}</th><th>${t('vaults.col_description')}</th><th>${t('vaults.col_tags')}</th><th></th></tr></thead>
          <tbody>${rows || emptyRow}</tbody>
        </table>
      </div>
    </div>`;

  // ── Event listeners ──────────────────────────────────────────────────────
  document.getElementById('btn-add-vault').addEventListener('click', () => showVaultModal(null));

  content.querySelectorAll('[data-edit]').forEach(btn => {
    const vault = vaults.find(v => v.id === Number(btn.dataset.edit));
    btn.addEventListener('click', () => showVaultModal(vault));
  });

  content.querySelectorAll('[data-delete]').forEach(btn => {
    const id   = Number(btn.dataset.delete);
    const desc = btn.dataset.desc;
    btn.addEventListener('click', () => {
      openConfirm(t('vaults.confirm_delete', { desc }), async () => {
        try {
          await deleteVault(id);
          showToast(t('vaults.toast_deleted'));
          render();
        } catch (err) {
          showToast(err.message, 'error');
        }
      });
    });
  });
}

function showVaultModal(vault) {
  const isEdit  = !!vault;

  const tagsSection = isEdit ? buildTagsSection(vault.tags) : '';

  const { overlay, close } = openModal(
    isEdit ? t('vaults.modal_edit') : t('vaults.modal_add'),
    `<form id="vault-form">
       <div class="form-field">
         <label for="vf-desc">${t('vaults.label_desc')}</label>
         <input id="vf-desc" name="description" type="text" required placeholder="${t('vaults.placeholder_desc')}"
           value="${isEdit ? escHtml(vault.description) : ''}" />
       </div>
       ${tagsSection}
       <div class="form-actions">
         <button type="button" class="btn btn-ghost" id="vf-cancel">${t('common.cancel')}</button>
         <button type="submit" class="btn btn-primary">${isEdit ? t('common.save') : t('common.create')}</button>
       </div>
     </form>`
  );
  lucide.createIcons();

  if (isEdit) {
    attachTagListeners(overlay, vault.tags, vault.id, addTagToVault, removeTagFromVault, _allTags);
  }

  overlay.querySelector('#vf-cancel').addEventListener('click', close);
  overlay.querySelector('#vault-form').addEventListener('submit', async e => {
    e.preventDefault();
    const desc = overlay.querySelector('#vf-desc').value.trim();
    try {
      if (isEdit) {
        await updateVault(vault.id, { description: desc });
        showToast(t('vaults.toast_updated'));
      } else {
        await createVault({ description: desc });
        showToast(t('vaults.toast_created'));
      }
      close();
      render();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  overlay.querySelector('#vf-desc').focus();
}
