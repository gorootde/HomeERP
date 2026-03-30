<script>
  import { onMount } from 'svelte';
  import { t } from '$lib/i18n.js';
  import { showToast } from '$lib/toast.js';
  import { getVaults, createVault, updateVault, deleteVault, addTagToVault, removeTagFromVault } from '$lib/api.js';
  import Modal from '$lib/components/Modal.svelte';
  import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
  import TagChips from '$lib/components/TagChips.svelte';
  import { Plus, Pencil, Trash2, ChevronLeft } from 'lucide-svelte';

  let vaults = $state([]);
  let loading = $state(true);
  let editModal = $state(null);
  let confirmDelete = $state(null);
  let form = $state({ description: '', tags: [] });

  onMount(async () => { await reload(); });

  async function reload() {
    loading = true;
    try { vaults = await getVaults(); } finally { loading = false; }
  }

  function openAdd() {
    form = { description: '', tags: [] };
    editModal = { vault: null, isNew: true };
  }

  function openEdit(v) {
    form = { description: v.description, tags: [...(v.tags || [])] };
    editModal = { vault: v, isNew: false };
  }

  async function save() {
    try {
      if (editModal.isNew) {
        await createVault({ description: form.description });
        showToast(t('vaults.toast_created'), 'success');
      } else {
        await updateVault(editModal.vault.id, { description: form.description });
        showToast(t('vaults.toast_updated'), 'success');
      }
      editModal = null;
      await reload();
    } catch (e) { showToast(String(e), 'error'); }
  }

  async function doDelete() {
    try {
      await deleteVault(confirmDelete.id);
      showToast(t('vaults.toast_deleted'), 'success');
      confirmDelete = null;
      await reload();
    } catch (e) { showToast(String(e), 'error'); }
  }

  async function addTag(name) {
    if (!editModal?.vault) { form.tags = [...form.tags, { id: Date.now(), name }]; return; }
    await addTagToVault(editModal.vault.id, name);
    const updated = (await getVaults()).find(v => v.id === editModal.vault.id);
    form.tags = [...(updated?.tags || [])];
  }

  async function removeTag(name) {
    if (!editModal?.vault) { form.tags = form.tags.filter(t => t.name !== name); return; }
    await removeTagFromVault(editModal.vault.id, name);
    const updated = (await getVaults()).find(v => v.id === editModal.vault.id);
    form.tags = [...(updated?.tags || [])];
  }
</script>

<div class="px-4 md:px-6 py-5 max-w-2xl">
  <div class="flex items-center gap-3 mb-5">
    <a href="/settings" class="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500"><ChevronLeft size={20} /></a>
    <h1 class="text-xl font-bold text-gray-900 flex-1">{t('vaults.title')}</h1>
    <button onclick={openAdd}
      class="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700">
      <Plus size={16} /> {t('vaults.btn_add')}
    </button>
  </div>

  {#if loading}
    <div class="flex justify-center py-16 text-gray-400">Loading…</div>
  {:else if vaults.length === 0}
    <p class="text-center text-gray-400 py-12">{t('vaults.empty')}</p>
  {:else}
    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-gray-200 bg-gray-50">
            <th class="text-left px-4 py-2.5 text-xs font-semibold text-gray-500">{t('vaults.col_id')}</th>
            <th class="text-left px-4 py-2.5 text-xs font-semibold text-gray-500">{t('vaults.col_description')}</th>
            <th class="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 hidden sm:table-cell">{t('vaults.col_tags')}</th>
            <th class="px-4 py-2.5"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          {#each vaults as v}
            <tr class="hover:bg-gray-50">
              <td class="px-4 py-2.5 text-gray-500 font-mono text-xs">{v.id}</td>
              <td class="px-4 py-2.5 font-medium text-gray-900">{v.description}</td>
              <td class="px-4 py-2.5 hidden sm:table-cell">
                <div class="flex flex-wrap gap-1">
                  {#each v.tags || [] as tag}
                    <span class="text-xs bg-blue-100 text-blue-700 rounded-full px-2 py-0.5">{tag.name}</span>
                  {/each}
                </div>
              </td>
              <td class="px-4 py-2.5">
                <div class="flex gap-1 justify-end">
                  <button onclick={() => openEdit(v)} class="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100">
                    <Pencil size={15} />
                  </button>
                  <button onclick={() => confirmDelete = { id: v.id }}
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
  <Modal title={editModal.isNew ? t('vaults.modal_add') : t('vaults.modal_edit')} onclose={() => editModal = null}>
    <div class="space-y-4">
      <div>
        <label class="block text-xs font-medium text-gray-700 mb-1">{t('vaults.label_desc')}</label>
        <input bind:value={form.description} placeholder={t('vaults.placeholder_desc')}
          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
      </div>
      <div>
        <label class="block text-xs font-medium text-gray-700 mb-1">{t('common.tags_label')}</label>
        <TagChips tags={form.tags} onadd={addTag} onremove={removeTag} />
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
  <ConfirmDialog message={t('vaults.confirm_delete')} onconfirm={doDelete} oncancel={() => confirmDelete = null} />
{/if}
