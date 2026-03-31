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
  import StockEntryModal from '$lib/components/StockEntryModal.svelte';
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

  let stockIdInput = $state('');
  let stockIdScannerActive = $state(false);
  let stockIdList = $state([]);

  // editModal.initial holds the pre-filled form values passed into StockEntryModal
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

  function openAdd() {
    editModal = { entry: null, isNew: true, initial: { quantity: '1' } };
  }

  function openEdit(e) {
    editModal = {
      entry: e,
      isNew: false,
      initial: {
        product_id: e.product_id,
        vault_id: e.vault_id,
        quantity: e.quantity,
        entry_unit_id: 'base',
        best_before_date: e.best_before_date || '',
        comment: e.comment || ''
      }
    };
  }

  async function save(data) {
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
  <StockEntryModal
    {products}
    {vaults}
    {units}
    initial={editModal.initial}
    isNew={editModal.isNew}
    onsave={save}
    onclose={() => editModal = null} />
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
