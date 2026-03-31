<script>
  import { onMount } from 'svelte';
  import { t } from '$lib/i18n.js';
  import { showToast } from '$lib/toast.js';
  import { getCategories, createCategory, updateCategory, deleteCategory, getUnits } from '$lib/api.js';
  import Modal from '$lib/components/Modal.svelte';
  import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
  import { Plus, Pencil, Trash2, ChevronLeft } from 'lucide-svelte';

  let categories = $state([]);
  let units = $state([]);
  let loading = $state(true);
  let editModal = $state(null);
  let confirmDelete = $state(null);
  let form = $state({ name: '', min_stock_quantity: '', min_stock_unit_id: '' });

  onMount(async () => { await reload(); });

  async function reload() {
    loading = true;
    try { [categories, units] = await Promise.all([getCategories(), getUnits()]); }
    finally { loading = false; }
  }

  function openAdd() {
    form = { name: '', min_stock_quantity: '', min_stock_unit_id: '' };
    editModal = { category: null, isNew: true };
  }

  function openEdit(c) {
    form = { name: c.name, min_stock_quantity: c.min_stock_quantity ?? '', min_stock_unit_id: c.min_stock_unit_id ?? '' };
    editModal = { category: c, isNew: false };
  }

  async function save() {
    const data = {
      name: form.name,
      min_stock_quantity: form.min_stock_quantity !== '' ? Number(form.min_stock_quantity) : null,
      min_stock_unit_id: form.min_stock_unit_id ? Number(form.min_stock_unit_id) : null
    };
    try {
      if (editModal.isNew) { await createCategory(data); showToast(t('categories.toast_created'), 'success'); }
      else { await updateCategory(editModal.category.id, data); showToast(t('categories.toast_saved'), 'success'); }
      editModal = null;
      await reload();
    } catch (e) { showToast(String(e), 'error'); }
  }

  async function doDelete() {
    try {
      await deleteCategory(confirmDelete.id);
      showToast(t('categories.toast_deleted'), 'success');
      confirmDelete = null;
      await reload();
    } catch (e) { showToast(String(e), 'error'); }
  }
</script>

<div class="px-4 md:px-6 py-5 max-w-2xl">
  <div class="flex items-center gap-3 mb-5">
    <a href="/settings" class="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500"><ChevronLeft size={20} /></a>
    <h1 class="text-xl font-bold text-gray-900 flex-1">{t('categories.title')}</h1>
    <button onclick={openAdd}
      class="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700">
      <Plus size={16} /> {t('categories.btn_add')}
    </button>
  </div>

  {#if loading}
    <div class="flex justify-center py-16 text-gray-400">Loading…</div>
  {:else if categories.length === 0}
    <p class="text-center text-gray-400 py-12">{t('categories.empty')}</p>
  {:else}
    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-gray-200 bg-gray-50">
            <th class="text-left px-4 py-2.5 text-xs font-semibold text-gray-500">{t('categories.col_name')}</th>
            <th class="text-left px-4 py-2.5 text-xs font-semibold text-gray-500">{t('categories.col_min_stock')}</th>
            <th class="px-4 py-2.5"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          {#each categories as c}
            <tr class="hover:bg-gray-50">
              <td class="px-4 py-2.5 font-medium text-gray-900">{c.name}</td>
              <td class="px-4 py-2.5 text-gray-500">
                {c.min_stock_quantity != null ? `${c.min_stock_quantity} ${c.min_stock_unit?.abbreviation || ''}` : '—'}
              </td>
              <td class="px-4 py-2.5">
                <div class="flex gap-1 justify-end">
                  <button onclick={() => openEdit(c)} class="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100">
                    <Pencil size={15} />
                  </button>
                  <button onclick={() => confirmDelete = { id: c.id }}
                    class="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50">
                    <Trash2 size={15} />
                  </button>
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>

{#if editModal}
  <Modal title={editModal.isNew ? t('categories.modal_add') : t('categories.modal_edit')} onclose={() => editModal = null}>
    <div class="space-y-4">
      <div>
        <label class="block text-xs font-medium text-gray-700 mb-1">{t('categories.label_name')}</label>
        <input bind:value={form.name} placeholder={t('categories.placeholder_name')}
          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
      </div>
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1">{t('categories.label_min_qty')}</label>
          <input bind:value={form.min_stock_quantity} type="number" step="any" placeholder={t('categories.placeholder_min_qty')}
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1">{t('categories.label_unit')}</label>
          <select bind:value={form.min_stock_unit_id}
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
            <option value="">{t('common.unit_placeholder')}</option>
            {#each units as u}
              <option value={u.id}>{u.name} ({u.abbreviation})</option>
            {/each}
          </select>
        </div>
      </div>
      <div class="flex justify-end gap-2 pt-2 border-t border-gray-100">
        <button onclick={() => editModal = null}
          class="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">{t('common.cancel')}</button>
        <button onclick={save}
          class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium">
          {editModal.isNew ? t('common.create') : t('common.save')}
        </button>
      </div>
    </div>
  </Modal>
{/if}

{#if confirmDelete}
  <ConfirmDialog message={t('categories.confirm_delete')} onconfirm={doDelete} oncancel={() => confirmDelete = null} />
{/if}
