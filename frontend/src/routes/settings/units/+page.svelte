<script>
  import { onMount } from 'svelte';
  import { t } from '$lib/i18n.js';
  import { showToast } from '$lib/toast.js';
  import { getUnits, createUnit, updateUnit, deleteUnit, addUnitConversion, deleteUnitConversion } from '$lib/api.js';
  import { fmtFactor } from '$lib/utils.js';
  import Modal from '$lib/components/Modal.svelte';
  import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
  import UnitConversionEditor from '$lib/components/UnitConversionEditor.svelte';
  import { Plus, Pencil, Trash2, ChevronLeft } from 'lucide-svelte';

  let units = $state([]);
  let loading = $state(true);
  let editModal = $state(null);
  let confirmDelete = $state(null);
  let form = $state({ name: '', abbreviation: '', conversions: [] });

  onMount(async () => { await reload(); });

  async function reload() {
    loading = true;
    try { units = await getUnits(); } finally { loading = false; }
  }

  function openAdd() {
    form = { name: '', abbreviation: '', conversions: [] };
    editModal = { unit: null, isNew: true };
  }

  function openEdit(u) {
    form = { name: u.name, abbreviation: u.abbreviation, conversions: [...(u.conversions || [])] };
    editModal = { unit: u, isNew: false };
  }

  async function save() {
    const data = { name: form.name, abbreviation: form.abbreviation };
    try {
      if (editModal.isNew) { await createUnit(data); showToast(t('units.toast_created'), 'success'); }
      else { await updateUnit(editModal.unit.id, data); showToast(t('units.toast_saved'), 'success'); }
      editModal = null;
      await reload();
    } catch (e) { showToast(String(e), 'error'); }
  }

  async function doDelete() {
    try {
      await deleteUnit(confirmDelete.id);
      showToast(t('units.toast_deleted'), 'success');
      confirmDelete = null;
      await reload();
    } catch (e) { showToast(String(e), 'error'); }
  }

  async function addConv({ factor, to_unit_id }) {
    try {
      await addUnitConversion(editModal.unit.id, { factor, to_unit_id });
      showToast(t('units.toast_conv_saved'), 'success');
      const updated = (await getUnits()).find(u => u.id === editModal.unit.id);
      form.conversions = [...(updated?.conversions || [])];
    } catch (e) { showToast(String(e), 'error'); }
  }

  async function removeConv(convId) {
    try {
      await deleteUnitConversion(editModal.unit.id, convId);
      showToast(t('units.toast_conv_deleted'), 'success');
      const updated = (await getUnits()).find(u => u.id === editModal.unit.id);
      form.conversions = [...(updated?.conversions || [])];
    } catch (e) { showToast(String(e), 'error'); }
  }

  let otherUnits = $derived(editModal?.unit ? units.filter(u => u.id !== editModal.unit.id) : units);
</script>

<div class="px-4 md:px-6 py-5 max-w-2xl">
  <div class="flex items-center gap-3 mb-5">
    <a href="/settings" class="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500"><ChevronLeft size={20} /></a>
    <h1 class="text-xl font-bold text-gray-900 flex-1">{t('units.title')}</h1>
    <button onclick={openAdd}
      class="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700">
      <Plus size={16} /> {t('units.btn_add')}
    </button>
  </div>

  {#if loading}
    <div class="flex justify-center py-16 text-gray-400">Loading…</div>
  {:else if units.length === 0}
    <p class="text-center text-gray-400 py-12">{t('units.empty')}</p>
  {:else}
    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-gray-200 bg-gray-50">
            <th class="text-left px-4 py-2.5 text-xs font-semibold text-gray-500">{t('units.col_name')}</th>
            <th class="text-left px-4 py-2.5 text-xs font-semibold text-gray-500">{t('units.col_abbr')}</th>
            <th class="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 hidden sm:table-cell">{t('units.col_conversions')}</th>
            <th class="px-4 py-2.5"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          {#each units as u}
            <tr class="hover:bg-gray-50">
              <td class="px-4 py-2.5 font-medium text-gray-900">{u.name}</td>
              <td class="px-4 py-2.5 text-gray-600 font-mono">{u.abbreviation}</td>
              <td class="px-4 py-2.5 text-gray-500 hidden sm:table-cell">
                {(u.conversions || []).length}
                {(u.conversions || []).length === 1 ? t('units.conv_count_singular') : t('units.conv_count_plural')}
              </td>
              <td class="px-4 py-2.5">
                <div class="flex gap-1 justify-end">
                  <button onclick={() => openEdit(u)} class="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100">
                    <Pencil size={15} />
                  </button>
                  <button onclick={() => confirmDelete = { id: u.id }}
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
  <Modal title={editModal.isNew ? t('units.modal_add') : t('units.modal_edit')} onclose={() => editModal = null}>
    <div class="space-y-4">
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1">{t('units.label_name')}</label>
          <input bind:value={form.name} placeholder={t('units.placeholder_name')}
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1">{t('units.label_abbr')}</label>
          <input bind:value={form.abbreviation} placeholder={t('units.placeholder_abbr')}
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
      </div>

      <!-- Conversions (only for existing units) -->
      {#if !editModal.isNew}
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-2">{t('units.label_conversions')}</label>
          <UnitConversionEditor
            conversions={form.conversions}
            units={otherUnits}
            fromAbbr={editModal.unit.abbreviation}
            onadd={addConv}
            onremove={removeConv} />
        </div>
      {/if}

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
  <ConfirmDialog message={t('units.confirm_delete')} onconfirm={doDelete} oncancel={() => confirmDelete = null} />
{/if}
