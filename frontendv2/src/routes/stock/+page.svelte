<script>
  import { onMount } from 'svelte';
  import { t } from '$lib/i18n.js';
  import { showToast } from '$lib/toast.js';
  import {
    getStockEntries, createStockEntry, updateStockEntry, deleteStockEntry,
    getVaults, getProducts, addStockId, removeStockId, getUnits
  } from '$lib/api.js';
  import { fmtQty, fmtDate } from '$lib/utils.js';
  import Modal from '$lib/components/Modal.svelte';
  import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
  import BarcodeScanner from '$lib/components/BarcodeScanner.svelte';
  import { Plus, Pencil, Trash2, QrCode, X } from 'lucide-svelte';

  let entries = $state([]);
  let vaults = $state([]);
  let products = $state([]);
  let units = $state([]);
  let loading = $state(true);

  let filterVault = $state('');
  let filterProduct = $state('');
  let filterExpiry = $state('');

  let editModal = $state(null);
  let stockIdModal = $state(null);
  let confirmDelete = $state(null);

  let form = $state({ product_id: '', vault_id: '', quantity: '1', entry_unit_id: 'base', best_before_date: '', comment: '' });
  let stockIdInput = $state('');
  let stockIdScannerActive = $state(false);
  let stockIdList = $state([]);

  // When product changes in form, reset entry_unit_id to that product's configured default
  $effect(() => {
    if (!editModal?.isNew) return;
    const product = products.find(p => p.id === Number(form.product_id));
    form.entry_unit_id = product?.entry_unit_key || 'base';
  });

  // All selectable units for the entry form: base unit + product conversions + global units with known factor
  let entryUnits = $derived(() => {
    const product = products.find(p => p.id === Number(form.product_id));
    if (!product?.unit) return [];
    const baseUnitId = product.unit.id;
    const result = [{ id: 'base', label: product.unit.name, abbreviation: product.unit.abbreviation, factor: 1 }];
    // Product-specific conversions: 1 puc = factor × base
    for (const puc of product.unit_conversions || []) {
      result.push({ id: 'puc_' + puc.id, label: puc.unit_name, abbreviation: puc.unit_name, factor: puc.factor });
    }
    // Global units that have a direct conversion to the product's base unit
    for (const u of units) {
      if (u.id === baseUnitId) continue;
      const conv = (u.conversions || []).find(c => c.to_unit?.id === baseUnitId);
      if (conv) {
        result.push({ id: 'global_' + u.id, label: u.name, abbreviation: u.abbreviation, factor: conv.factor });
      }
    }
    return result;
  });

  let filtered = $derived(() => {
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    return entries.filter(e => {
      if (filterVault && e.vault_id !== Number(filterVault)) return false;
      if (filterProduct && e.product_id !== Number(filterProduct)) return false;
      if (filterExpiry) {
        if (!e.best_before_date) return false;
        const bbd = new Date(e.best_before_date);
        const cutoff = new Date(now);
        cutoff.setDate(cutoff.getDate() + Number(filterExpiry));
        if (bbd < now || bbd > cutoff) return false;
      }
      return true;
    });
  });

  onMount(async () => { await reload(); });

  async function reload() {
    loading = true;
    try {
      [entries, vaults, products, units] = await Promise.all([
        getStockEntries(), getVaults(), getProducts('', 500), getUnits()
      ]);
    } finally {
      loading = false;
    }
  }

  function openAdd(productId = '') {
    const product = productId ? products.find(p => p.id === Number(productId)) : null;
    const defaultUnit = product?.entry_unit_key || 'base';
    form = { product_id: productId ? String(productId) : '', vault_id: '', quantity: '1', entry_unit_id: defaultUnit, best_before_date: '', comment: '' };
    editModal = { entry: null, isNew: true };
  }

  function openEdit(e) {
    form = {
      product_id: e.product_id,
      vault_id: e.vault_id,
      quantity: e.quantity,
      entry_unit_id: 'base',
      best_before_date: e.best_before_date || '',
      comment: e.comment || ''
    };
    editModal = { entry: e, isNew: false };
  }

  async function save() {
    const eu = entryUnits().find(u => u.id === form.entry_unit_id);
    const factor = eu?.factor ?? 1;
    const data = {
      product_id: Number(form.product_id),
      vault_id: Number(form.vault_id),
      quantity: Number(form.quantity) * factor,
      best_before_date: form.best_before_date || null,
      comment: form.comment || null
    };
    try {
      if (editModal.isNew) {
        await createStockEntry(data);
        showToast(t('stock.toast_added'), 'success');
      } else {
        await updateStockEntry(editModal.entry.id, data);
        showToast(t('stock.toast_updated'), 'success');
      }
      editModal = null;
      await reload();
    } catch (e) {
      showToast(String(e), 'error');
    }
  }

  async function doDelete() {
    try {
      await deleteStockEntry(confirmDelete.id);
      showToast(t('stock.toast_deleted'), 'success');
      confirmDelete = null;
      await reload();
    } catch (e) {
      showToast(String(e), 'error');
    }
  }

  // Stock ID modal
  function openStockIdModal(entry) {
    stockIdList = [...(entry.stock_ids || [])];
    stockIdInput = '';
    stockIdScannerActive = false;
    stockIdModal = { entry };
  }

  async function addSid() {
    const code = stockIdInput.trim();
    if (!code) return;
    try {
      await addStockId(stockIdModal.entry.id, code);
      showToast(t('stock.stockid_toast_added'), 'success');
      const updated = entries.find(e => e.id === stockIdModal.entry.id);
      if (updated) {
        const fresh = await getStockEntries();
        entries = fresh;
        const refreshed = fresh.find(e => e.id === stockIdModal.entry.id);
        if (refreshed) stockIdList = [...(refreshed.stock_ids || [])];
      }
      stockIdInput = '';
    } catch (e) {
      showToast(String(e), 'error');
    }
  }

  async function removeSid(sid) {
    await removeStockId(stockIdModal.entry.id, sid);
    showToast(t('stock.stockid_toast_removed'), 'success');
    const fresh = await getStockEntries();
    entries = fresh;
    const refreshed = fresh.find(e => e.id === stockIdModal.entry.id);
    if (refreshed) stockIdList = [...(refreshed.stock_ids || [])];
  }

  function handleSidScan(code) {
    stockIdInput = code;
    stockIdScannerActive = false;
    addSid();
  }

  function bbdClass(dateStr) {
    if (!dateStr) return '';
    const now = new Date(); now.setHours(0,0,0,0);
    const bbd = new Date(dateStr);
    const diff = Math.ceil((bbd - now) / 86400000);
    if (diff < 0) return 'text-red-600 font-medium';
    if (diff <= 7) return 'text-red-500';
    if (diff <= 30) return 'text-yellow-600';
    return 'text-gray-600';
  }
</script>

<div class="px-4 md:px-6 py-5 max-w-5xl">
  <!-- Header -->
  <div class="flex flex-wrap items-center gap-3 mb-4">
    <h1 class="text-xl font-bold text-gray-900 flex-1">{t('stock.title')}</h1>
    <button onclick={openAdd}
      class="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 shrink-0">
      <Plus size={16} /> {t('stock.btn_add')}
    </button>
  </div>

  <!-- Filters -->
  <div class="flex flex-wrap gap-2 mb-4">
    <select bind:value={filterVault}
      class="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
      <option value="">{t('stock.filter_all_vaults')}</option>
      {#each vaults as v}
        <option value={v.id}>{v.description}</option>
      {/each}
    </select>
    <select bind:value={filterProduct}
      class="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
      <option value="">{t('stock.filter_all_products')}</option>
      {#each products as p}
        <option value={p.id}>{p.name}</option>
      {/each}
    </select>
    <select bind:value={filterExpiry}
      class="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
      <option value="">{t('stock.filter_expiry_all')}</option>
      <option value="7">{t('stock.filter_expiry_7d')}</option>
      <option value="30">{t('stock.filter_expiry_30d')}</option>
      <option value="180">{t('stock.filter_expiry_6m')}</option>
    </select>
  </div>

  {#if loading}
    <div class="flex justify-center py-16 text-gray-400">Loading…</div>
  {:else}
    {@const rows = filtered()}
    {#if rows.length === 0}
      <p class="text-center text-gray-400 py-12">
        {filterVault || filterProduct || filterExpiry ? t('stock.empty_filter') : t('stock.empty')}
      </p>
    {:else}
      <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-gray-200 bg-gray-50">
                <th class="text-left px-4 py-2.5 text-xs font-semibold text-gray-500">{t('stock.col_product')}</th>
                <th class="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 hidden sm:table-cell">{t('stock.col_vault')}</th>
                <th class="text-right px-4 py-2.5 text-xs font-semibold text-gray-500">{t('stock.col_qty')}</th>
                <th class="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 hidden md:table-cell">{t('stock.col_bbd')}</th>
                <th class="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 hidden lg:table-cell">{t('stock.col_comment')}</th>
                <th class="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 hidden lg:table-cell">{t('stock.col_stockids')}</th>
                <th class="px-4 py-2.5"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              {#each rows as e}
                <tr class="hover:bg-gray-50">
                  <td class="px-4 py-2.5">
                    <p class="font-medium text-gray-900">{e.product?.name || '—'}</p>
                    <p class="text-xs text-gray-500 sm:hidden">{e.vault?.description || ''}</p>
                  </td>
                  <td class="px-4 py-2.5 text-gray-600 hidden sm:table-cell">{e.vault?.description || '—'}</td>
                  <td class="px-4 py-2.5 text-right font-semibold text-gray-900">
                    {fmtQty(e.quantity)} {e.product?.unit?.abbreviation || ''}
                  </td>
                  <td class="px-4 py-2.5 hidden md:table-cell">
                    <span class={bbdClass(e.best_before_date)}>{fmtDate(e.best_before_date)}</span>
                  </td>
                  <td class="px-4 py-2.5 text-gray-500 hidden lg:table-cell">{e.comment || '—'}</td>
                  <td class="px-4 py-2.5 hidden lg:table-cell">
                    <div class="flex flex-wrap gap-1">
                      {#each e.stock_ids || [] as sid}
                        <span class="text-xs font-mono bg-gray-100 text-gray-600 rounded px-1.5 py-0.5">{sid.code}</span>
                      {/each}
                    </div>
                  </td>
                  <td class="px-4 py-2.5">
                    <div class="flex items-center gap-1 justify-end">
                      <button onclick={() => openStockIdModal(e)} title={t('stock.col_stockids')}
                        class="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100">
                        <QrCode size={15} />
                      </button>
                      <button onclick={() => openEdit(e)}
                        class="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100">
                        <Pencil size={15} />
                      </button>
                      <button onclick={() => confirmDelete = { id: e.id }}
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
      </div>
    {/if}
  {/if}
</div>

<!-- Edit/Add Modal -->
{#if editModal}
  <Modal title={editModal.isNew ? t('stock.modal_add') : t('stock.modal_edit')} onclose={() => editModal = null}>
    <div class="space-y-4">
      <div>
        <label class="block text-xs font-medium text-gray-700 mb-1">{t('stock.label_product')}</label>
        <select bind:value={form.product_id}
          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
          <option value="">{t('stock.select_product')}</option>
          {#each products as p}
            <option value={p.id}>{p.name}</option>
          {/each}
        </select>
      </div>
      <div>
        <label class="block text-xs font-medium text-gray-700 mb-1">{t('stock.label_vault')}</label>
        <select bind:value={form.vault_id}
          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
          <option value="">{t('stock.select_vault')}</option>
          {#each vaults as v}
            <option value={v.id}>{v.description}</option>
          {/each}
        </select>
      </div>
      <div>
        <label class="block text-xs font-medium text-gray-700 mb-1">{t('stock.label_qty')}</label>
        <div class="flex gap-2">
          <div class="flex rounded-lg border border-gray-300 focus-within:ring-2 focus-within:ring-blue-500 overflow-hidden flex-1">
            <input bind:value={form.quantity} type="number" step="any"
              class="flex-1 px-3 py-2 text-sm focus:outline-none min-w-0" />
          </div>
          {#if entryUnits().length > 1}
            <select bind:value={form.entry_unit_id}
              class="px-2 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
              {#each entryUnits() as u}
                <option value={u.id}>{u.abbreviation}</option>
              {/each}
            </select>
          {:else if entryUnits().length === 1}
            <span class="px-3 py-2 text-sm text-gray-500 bg-gray-100 border border-gray-300 rounded-lg shrink-0 flex items-center">
              {entryUnits()[0].abbreviation}
            </span>
          {/if}
        </div>
      </div>
      <div>
        <label class="block text-xs font-medium text-gray-700 mb-1">{t('stock.label_bbd')}</label>
        <input bind:value={form.best_before_date} type="date"
          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
      </div>
      <div>
        <label class="block text-xs font-medium text-gray-700 mb-1">{t('stock.label_comment')}</label>
        <input bind:value={form.comment} placeholder={t('stock.placeholder_comment')}
          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
      </div>
      <div class="flex justify-end gap-2 pt-2 border-t border-gray-100">
        <button onclick={() => editModal = null}
          class="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
          {t('common.cancel')}
        </button>
        <button onclick={save}
          class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium">
          {editModal.isNew ? t('common.create') : t('common.save')}
        </button>
      </div>
    </div>
  </Modal>
{/if}

<!-- Stock ID Modal -->
{#if stockIdModal}
  <Modal title={t('stock.stockid_modal_title')} onclose={() => { stockIdModal = null; stockIdScannerActive = false; }}>
    <div class="space-y-4">
      <p class="text-sm text-gray-500">{t('stock.stockid_modal_hint')}</p>
      {#if stockIdList.length > 0}
        <div class="flex flex-wrap gap-2">
          {#each stockIdList as sid}
            <span class="inline-flex items-center gap-1.5 font-mono text-xs bg-gray-100 rounded-md px-2.5 py-1">
              {sid.code}
              <button onclick={() => removeSid(sid.id)} class="text-gray-400 hover:text-red-600"><X size={12} /></button>
            </span>
          {/each}
        </div>
      {/if}
      {#if stockIdScannerActive}
        <BarcodeScanner active={true} onscan={handleSidScan} />
        <button onclick={() => stockIdScannerActive = false}
          class="w-full py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
          {t('stock.stockid_btn_stop')}
        </button>
      {:else}
        <div class="flex gap-2">
          <input bind:value={stockIdInput} placeholder={t('stock.stockid_placeholder')}
            onkeydown={(e) => e.key === 'Enter' && addSid()}
            class="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <button onclick={addSid}
            class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            {t('common.add')}
          </button>
          <button onclick={() => stockIdScannerActive = true}
            class="px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
            {t('stock.stockid_btn_scan')}
          </button>
        </div>
      {/if}
      <div class="flex justify-end pt-1">
        <button onclick={() => { stockIdModal = null; stockIdScannerActive = false; }}
          class="px-4 py-2 text-sm bg-gray-800 text-white rounded-lg hover:bg-gray-700">
          {t('stock.stockid_btn_done')}
        </button>
      </div>
    </div>
  </Modal>
{/if}

<!-- Confirm Delete -->
{#if confirmDelete}
  <ConfirmDialog
    message={t('stock.confirm_delete')}
    onconfirm={doDelete}
    oncancel={() => confirmDelete = null} />
{/if}
