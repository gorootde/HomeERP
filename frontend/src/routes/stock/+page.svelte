<script>
  import { onMount } from 'svelte';
  import { t } from '$lib/i18n.js';
  import { showToast } from '$lib/toast.js';
  import {
    getStockEntries, createStockEntry, updateStockEntry, deleteStockEntry,
    getVaults, getProducts, addStockId, removeStockId, getUnits, getSetting,
    getEntryMovements, undoStockMovement, printStockEntryLabel
  } from '$lib/api.js';
  import { fmtQty, fmtDate, fmtProductLabel } from '$lib/utils.js';
  import Modal from '$lib/components/Modal.svelte';
  import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
  import ScannableCodeList from '$lib/components/ScannableCodeList.svelte';
  import FilterSelect from '$lib/components/FilterSelect.svelte';
  import ResponsiveTable from '$lib/components/ResponsiveTable.svelte';
  import StockEntryModal from '$lib/components/StockEntryModal.svelte';
  import MovementList from '$lib/components/MovementList.svelte';
  import { Plus, Pencil, Trash2, QrCode, History, Printer } from 'lucide-svelte';

  let entries = $state([]);
  let vaults = $state([]);
  let products = $state([]);
  let units = $state([]);
  let autoPrintEnabled = $state(false);
  let loading = $state(true);

  let filterVault = $state('');
  let filterProduct = $state('');
  let filterExpiry = $state('');

  let editModal = $state(null);
  let stockIdModal = $state(null);
  let confirmDelete = $state(null);
  let historyModal = $state(null);
  let historyRows = $state([]);
  let historyLoading = $state(false);
  let historyBusyId = $state(null);
  let printingId = $state(null);

  let stockIdInput = $state('');
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
      let autoPrintSetting;
      [entries, vaults, products, units, autoPrintSetting] = await Promise.all([
        getStockEntries(), getVaults(), getProducts('', 500), getUnits(),
        getSetting('label_auto_print')
      ]);
      autoPrintEnabled = autoPrintSetting?.value === '1';
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

  async function reprintLabel(entry) {
    printingId = entry.id;
    try {
      await printStockEntryLabel(entry.id);
      showToast(t('stock.toast_label_printed'), 'success');
    } catch {
      showToast(t('stock.toast_label_print_failed'), 'error');
    } finally {
      printingId = null;
    }
  }

  // Stock ID modal
  function openStockIdModal(entry) {
    stockIdList = [...(entry.stock_ids || [])];
    stockIdInput = '';
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
    addSid();
  }

  // Per-entry movement history
  async function openHistory(entry) {
    historyModal = { entry };
    historyLoading = true;
    historyRows = [];
    try {
      historyRows = await getEntryMovements(entry.id);
    } catch (e) {
      showToast(String(e), 'error');
    } finally {
      historyLoading = false;
    }
  }

  async function undoFromHistory(id) {
    historyBusyId = id;
    try {
      await undoStockMovement(id);
      showToast(t('history.toast_undone'), 'success');
      historyRows = await getEntryMovements(historyModal.entry.id);
      await reload();
    } catch (e) {
      showToast(String(e), 'error');
    } finally {
      historyBusyId = null;
    }
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
    <FilterSelect bind:value={filterVault} placeholder={t('stock.filter_all_vaults')}
      options={vaults.map(v => ({ value: v.id, label: v.description }))} />
    <FilterSelect bind:value={filterProduct} placeholder={t('stock.filter_all_products')}
      options={products.map(p => ({ value: p.id, label: fmtProductLabel(p) }))} />
    <FilterSelect bind:value={filterExpiry} placeholder={t('stock.filter_expiry_all')}
      options={[
        { value: '7', label: t('stock.filter_expiry_7d') },
        { value: '30', label: t('stock.filter_expiry_30d') },
        { value: '180', label: t('stock.filter_expiry_6m') },
      ]} />
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
      {#snippet productCell(e)}
        <p class="font-medium text-gray-900">{e.product?.name || '—'}</p>
        {#if e.product?.vendor}
          <p class="text-xs text-gray-500">{e.product.vendor}</p>
        {/if}
        <p class="text-xs text-gray-500 sm:hidden">{e.vault?.description || ''}</p>
      {/snippet}
      {#snippet vaultCell(e)}<span class="text-gray-600">{e.vault?.description || '—'}</span>{/snippet}
      {#snippet qtyCell(e)}
        <span class="font-semibold text-gray-900">{fmtQty(e.quantity)} {e.product?.unit?.abbreviation || ''}</span>
      {/snippet}
      {#snippet bbdCell(e)}<span class={bbdClass(e.best_before_date)}>{fmtDate(e.best_before_date)}</span>{/snippet}
      {#snippet commentCell(e)}<span class="text-gray-500">{e.comment || '—'}</span>{/snippet}
      {#snippet stockIdsCell(e)}
        <div class="flex flex-wrap gap-1">
          {#each e.stock_ids || [] as sid}
            <span class="text-xs font-mono bg-gray-100 text-gray-600 rounded px-1.5 py-0.5">{sid.code}</span>
          {/each}
        </div>
      {/snippet}
      {#snippet actionsCell(e)}
        <div class="flex items-center gap-1 justify-end">
          <button onclick={() => openHistory(e)} aria-label={t('stock.col_history')} title={t('stock.col_history')}
            class="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100">
            <History size={15} />
          </button>
          <button onclick={() => openStockIdModal(e)} aria-label={t('stock.col_stockids')} title={t('stock.col_stockids')}
            class="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100">
            <QrCode size={15} />
          </button>
          <button onclick={() => reprintLabel(e)} disabled={printingId === e.id}
            aria-label={t('stock.btn_reprint_label')} title={t('stock.btn_reprint_label')}
            class="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 disabled:opacity-50">
            <Printer size={15} />
          </button>
          <button onclick={() => openEdit(e)} aria-label={t('common.edit')} title={t('common.edit')}
            class="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100">
            <Pencil size={15} />
          </button>
          <button onclick={() => confirmDelete = { id: e.id }} aria-label={t('common.delete')} title={t('common.delete')}
            class="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50">
            <Trash2 size={15} />
          </button>
        </div>
      {/snippet}
      <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <ResponsiveTable
          rows={rows}
          rowKey={(e) => e.id}
          columns={[
            { label: t('stock.col_product'), cell: productCell },
            { label: t('stock.col_vault'), hideBelow: 'sm', cell: vaultCell },
            { label: t('stock.col_qty'), align: 'right', cell: qtyCell },
            { label: t('stock.col_bbd'), hideBelow: 'md', cell: bbdCell },
            { label: t('stock.col_comment'), hideBelow: 'lg', cell: commentCell },
            { label: t('stock.col_stockids'), hideBelow: 'lg', cell: stockIdsCell },
            { cell: actionsCell },
          ]} />
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
    {autoPrintEnabled}
    onsave={save}
    onclose={() => editModal = null} />
{/if}

<!-- Stock ID Modal -->
{#if stockIdModal}
  <Modal title={t('stock.stockid_modal_title')} onclose={() => { stockIdModal = null; }}>
    <div class="space-y-4">
      <ScannableCodeList
        codes={stockIdList}
        bind:value={stockIdInput}
        hint={t('stock.stockid_modal_hint')}
        placeholder={t('stock.stockid_placeholder')}
        onadd={addSid}
        onremove={removeSid}
        onscan={handleSidScan} />
      <div class="flex justify-end pt-1">
        <button onclick={() => { stockIdModal = null; }}
          class="px-4 py-2 text-sm bg-gray-800 text-white rounded-lg hover:bg-gray-700">
          {t('stock.stockid_btn_done')}
        </button>
      </div>
    </div>
  </Modal>
{/if}

<!-- Movement history -->
{#if historyModal}
  <Modal title={t('stock.history_modal_title')} onclose={() => historyModal = null}>
    <div class="space-y-3">
      <p class="text-sm text-gray-500">
        {historyModal.entry.product?.name || '—'} · {historyModal.entry.vault?.description || '—'}
      </p>
      {#if historyLoading}
        <div class="py-8 text-center text-gray-400">Loading…</div>
      {:else if historyRows.length === 0}
        <p class="py-8 text-center text-gray-400">{t('history.empty')}</p>
      {:else}
        <div class="border border-gray-200 rounded-lg overflow-hidden">
          <MovementList movements={historyRows} showContext={false}
            busyId={historyBusyId} onundo={undoFromHistory} />
        </div>
      {/if}
      <div class="flex justify-end pt-1">
        <button onclick={() => historyModal = null}
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
