<script>
  import { onMount } from 'svelte';
  import { t } from '$lib/i18n.svelte.js';
  import { showToast } from '$lib/toast.js';
  import {
    getByEan, getEanInfo, getStockEntryByStockId, getProduct,
    createProduct, createStockEntry, updateStockEntry, deleteStockEntry, addProductUnitConversion,
    getVaults, getProducts, getUnits, getCategories, getSettings
  } from '$lib/api.js';
  import { fmtDate, fmtQty, isStockId, matchUnitFromOffSize, stagePucConversion } from '$lib/utils.js';
  import Modal from '$lib/components/Modal.svelte';
  import BarcodeScanner from '$lib/components/BarcodeScanner.svelte';
  import StockEntryModal from '$lib/components/StockEntryModal.svelte';
  import UnitConversionEditor from '$lib/components/UnitConversionEditor.svelte';
  import { ScanBarcode, QrCode, Package, Minus, Sliders } from 'lucide-svelte';

  let scannerActive = $state(true);
  let vaults = $state([]);
  let products = $state([]);
  let units = $state([]);
  let categories = $state([]);
  let settings = $state([]);

  // Scan result state
  let result = $state(null); // { type: 'stockid'|'ean_found'|'ean_unknown', data }
  let lastCode = $state('');

  // Modals
  let adjustModal = $state(null);
  let newProductModal = $state(null);
  let addEntryModal = $state(null);

  let adjustQty = $state('');
  let newProd = $state({ name: '', vendor: '', unit_id: '', category_id: '', puc: [] });

  // Pause the camera/scan loop while any modal is open — keeping it running
  // in the background is heavy and makes the browser noticeably sluggish.
  let scannerRunning = $derived(scannerActive && !adjustModal && !newProductModal && !addEntryModal);

  onMount(async () => {
    [vaults, products, units, categories, settings] = await Promise.all([
      getVaults(), getProducts('', 500), getUnits(), getCategories(), getSettings()
    ]);
    // Test-only hook: lets Playwright inject a scanned code without a real,
    // decodable barcode image (the fake camera device can't provide one).
    if (typeof window !== 'undefined' && window.__E2E_TEST_HOOKS__) {
      window.__scanCode = handleScan;
    }
  });

  function getSetting(key) {
    return settings.find(s => s.key === key)?.value || '';
  }

  async function handleScan(code) {
    code = code.trim();
    if (code === lastCode) return;
    lastCode = code;
    result = null;

    if (isStockId(code)) {
      try {
        const entry = await getStockEntryByStockId(code);
        result = { type: 'stockid', data: entry, code };
      } catch {
        result = { type: 'stockid_not_found', code };
      }
    } else {
      try {
        const product = await getByEan(code);
        result = { type: 'ean_found', data: product, code };
      } catch {
        // Unknown EAN — check OpenFoodFacts
        let offData = null;
        try { offData = await getEanInfo(code); } catch {}
        result = { type: 'ean_unknown', code, offData };
      }
    }
  }

  // Stock ID actions
  async function consume(entry) {
    const newQty = entry.quantity - 1;
    try {
      if (newQty <= 0) {
        await deleteStockEntry(entry.id, 'consume');
        showToast(t('scanner.toast_consumed_deleted'), 'success');
      } else {
        await updateStockEntry(entry.id, { quantity: newQty, reason: 'consume' });
        showToast(t('scanner.toast_consumed', { qty: fmtQty(entry.quantity) }), 'success');
      }
      result = null;
      lastCode = '';
    } catch (e) {
      showToast(String(e), 'error');
    }
  }

  function openAdjust(entry) {
    adjustQty = String(entry.quantity);
    adjustModal = { entry };
  }

  async function doAdjust() {
    const qty = parseFloat(adjustQty);
    if (isNaN(qty) || qty < 0) { showToast(t('scanner.err_invalid_qty'), 'error'); return; }
    try {
      if (qty === 0) {
        await deleteStockEntry(adjustModal.entry.id, 'adjust');
      } else {
        await updateStockEntry(adjustModal.entry.id, { quantity: qty, reason: 'adjust' });
      }
      showToast(t('scanner.toast_qty_updated'), 'success');
      adjustModal = null;
      result = null;
      lastCode = '';
    } catch (e) {
      showToast(String(e), 'error');
    }
  }

  // New product + entry flow
  function openNewProduct(code, offData) {
    const { numeric, matchedUnit } = matchUnitFromOffSize(units, offData?.size);
    newProd = {
      name: offData?.name || '',
      vendor: offData?.vendor || '',
      unit_id: matchedUnit ? matchedUnit.id : '',
      category_id: '',
      ean: code,
      puc: []
    };
    // Stage the OpenFoodFacts package size as a first named packaging unit
    // instead of a bare number, so it doesn't collide with a real Unit later.
    if (numeric && matchedUnit) {
      addNewProdPuc({ factor: parseFloat(numeric), to_unit_id: matchedUnit.id, name: t('common.unit_piece_label') });
    }
    newProductModal = { code, offData };
  }

  function addNewProdPuc({ factor, to_unit_id, name }) {
    if (!name?.trim()) { showToast(t('products.puc_err_name'), 'error'); return; }
    const staged = stagePucConversion({ factor, to_unit_id, name, units, pucUnits: newProd.puc });
    if (!staged) { showToast(t('products.puc_err_unit'), 'error'); return; }
    newProd.puc = [...newProd.puc, staged];
  }

  function removeNewProdPuc(convId) {
    newProd.puc = newProd.puc.filter(c => c.id !== convId);
  }

  async function createNewProduct() {
    try {
      let p = await createProduct({
        name: newProd.name,
        vendor: newProd.vendor || null,
        unit_id: newProd.unit_id ? Number(newProd.unit_id) : null,
        category_id: newProd.category_id ? Number(newProd.category_id) : null,
        ean_codes: newProd.ean ? [newProd.ean] : []
      });
      if (newProd.puc.length > 0) {
        for (const puc of newProd.puc) {
          await addProductUnitConversion(p.id, {
            unit_name: puc.unit_name,
            base_unit_id: puc.base_unit_id,
            factor: puc.factor
          });
        }
        p = await getProduct(p.id);
      }
      products = [...products, p];
      showToast(t('scanner.toast_product_created'), 'success');
      newProductModal = null;
      // Open add entry modal
      openAddEntry(p, newProd.ean);
    } catch (e) {
      showToast(String(e), 'error');
    }
  }

  function openAddEntry(product, ean) {
    addEntryModal = { product, ean };
  }

  function openCreateEntryForStockId(code) {
    addEntryModal = { stockId: code };
  }

  async function createEntry(data) {
    try {
      await createStockEntry(data);
      showToast(t('scanner.toast_entry_created'), 'success');
      addEntryModal = null;
      result = null;
      lastCode = '';
    } catch (e) {
      showToast(String(e), 'error');
    }
  }
</script>

<div class="px-4 md:px-6 py-5 max-w-lg mx-auto">
  <h1 class="text-xl font-bold text-gray-900 mb-5">{t('scanner.title')}</h1>

  <!-- Scanner -->
  <div class="bg-white rounded-xl border border-gray-200 p-4 mb-4">
    <BarcodeScanner active={scannerRunning} onscan={handleScan} />
    <button
      onclick={() => { scannerActive = !scannerActive; if (!scannerActive) { result = null; lastCode = ''; } }}
      class="mt-3 w-full py-2.5 text-sm font-medium rounded-lg border transition-colors
        {scannerActive ? 'bg-red-50 text-red-700 border-red-200 hover:bg-red-100' : 'bg-blue-600 text-white border-transparent hover:bg-blue-700'}">
      <span class="flex items-center justify-center gap-2">
        <ScanBarcode size={16} />
        {scannerActive ? t('inventory.btn_stop_scanner') : t('inventory.btn_start_scanner')}
      </span>
    </button>
  </div>

  <!-- Hints -->
  {#if !result}
    {@const stockPrefix = getSetting('stock_id_prefix')}
    {@const stockMode = getSetting('stock_id_mode')}
    <div class="grid grid-cols-2 gap-3">
      <div class="bg-gray-50 rounded-xl p-3 border border-gray-200">
        <p class="text-xs font-semibold text-gray-700 mb-0.5 flex items-center gap-1.5">
          <ScanBarcode size={13} class="shrink-0" /> {t('scanner.hint_ean_title')}
        </p>
        <p class="text-xs text-gray-500">{t('scanner.hint_ean_desc')}</p>
      </div>
      {#if stockMode === 'generated' && stockPrefix}
        <div class="bg-gray-50 rounded-xl p-3 border border-gray-200">
          <p class="text-xs font-semibold text-gray-700 mb-0.5 flex items-center gap-1.5">
            <QrCode size={13} class="shrink-0" /> {t('scanner.hint_stockid_title', { prefix: stockPrefix })}
          </p>
          <p class="text-xs text-gray-500">{t('scanner.hint_stockid_desc')}</p>
        </div>
      {/if}
    </div>
  {/if}

  <!-- Result -->
  {#if result}
    <div class="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
      {#if result.type === 'stockid'}
        {@const entry = result.data}
        <div class="flex items-center gap-2">
          <span class="text-xs font-medium bg-blue-100 text-blue-700 rounded-full px-2.5 py-0.5">{t('scanner.stockid_badge')}</span>
          <span class="font-mono text-sm text-gray-600">{result.code}</span>
        </div>
        <div>
          <p class="font-semibold text-gray-900">{entry.product?.name || '—'}</p>
          <p class="text-sm text-gray-500">{t('scanner.label_location')}: {entry.vault?.description || '—'}</p>
          <p class="text-sm text-gray-500">{t('scanner.label_stock')}: {fmtQty(entry.quantity)} {entry.product?.unit?.abbreviation || ''}</p>
          {#if entry.best_before_date}
            <p class="text-sm text-gray-500">{t('scanner.label_bbd')}: {fmtDate(entry.best_before_date)}</p>
          {/if}
        </div>
        <div class="flex gap-2">
          <button onclick={() => consume(entry)}
            class="flex-1 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            <span class="flex items-center justify-center gap-1"><Minus size={14} /> {t('scanner.btn_consume')}</span>
          </button>
          <button onclick={() => openAdjust(entry)}
            class="flex-1 py-2 text-sm font-medium border border-gray-300 rounded-lg hover:bg-gray-50">
            <span class="flex items-center justify-center gap-1"><Sliders size={14} /> {t('scanner.btn_adjust')}</span>
          </button>
        </div>

      {:else if result.type === 'stockid_not_found'}
        <p class="font-semibold text-gray-800">{t('scanner.stockid_not_found')}</p>
        <p class="text-sm text-gray-500">{t('scanner.stockid_not_found_hint')}</p>
        <p class="text-xs font-mono text-gray-400">{result.code}</p>
        <button onclick={() => openCreateEntryForStockId(result.code)}
          class="w-full py-2.5 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          {t('scanner.btn_create_entry')}
        </button>

      {:else if result.type === 'ean_found'}
        {@const product = result.data}
        <p class="text-xs font-medium text-green-600">{t('scanner.ean_found')}</p>
        <div class="flex items-center gap-3">
          {#if product.image_path}
            <img src={product.image_path} alt={product.name}
              class="w-12 h-12 rounded-lg object-cover bg-gray-100" />
          {:else}
            <div class="w-12 h-12 rounded-lg bg-gray-100 flex items-center justify-center">
              <Package size={20} class="text-gray-400" />
            </div>
          {/if}
          <div>
            <p class="font-semibold text-gray-900">{product.name}</p>
            {#if product.vendor}<p class="text-sm text-gray-500">{product.vendor}</p>{/if}
          </div>
        </div>
        <button onclick={() => openAddEntry(product, result.code)}
          class="w-full py-2.5 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          {t('scanner.btn_add_entry')}
        </button>

      {:else if result.type === 'ean_unknown'}
        <p class="text-xs font-medium text-amber-600">{t('scanner.ean_unknown_heading')}</p>
        <p class="text-sm text-gray-700">{t('scanner.ean_unknown_hint')}</p>
        <p class="font-mono text-sm text-gray-500">{result.code}</p>
        {#if result.offData}
          <div class="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm">
            <p class="font-medium text-amber-800">{t('scanner.off_banner_label')}: {result.offData.name}</p>
          </div>
        {/if}
        <button onclick={() => openNewProduct(result.code, result.offData)}
          class="w-full py-2.5 text-sm font-medium bg-gray-800 text-white rounded-lg hover:bg-gray-700">
          {t('scanner.btn_new_product')}
        </button>
      {/if}

      <button onclick={() => { result = null; lastCode = ''; }}
        class="w-full py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
        {t('scanner.btn_continue')}
      </button>
    </div>
  {/if}
</div>

<!-- Adjust Qty Modal -->
{#if adjustModal}
  <Modal title={t('scanner.adjust_modal_title')} onclose={() => adjustModal = null}>
    <div class="space-y-4">
      <div>
        <label class="block text-xs font-medium text-gray-700 mb-1">{t('scanner.label_new_qty')}</label>
        <input bind:value={adjustQty} type="number" step="any"
          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
      </div>
      <div class="flex justify-end gap-2">
        <button onclick={() => adjustModal = null}
          class="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">{t('common.cancel')}</button>
        <button onclick={doAdjust}
          class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium">{t('common.save')}</button>
      </div>
    </div>
  </Modal>
{/if}

<!-- New Product Modal -->
{#if newProductModal}
  <Modal title={t('scanner.new_product_modal')} onclose={() => newProductModal = null}>
    <div class="space-y-4">
      <div>
        <label class="block text-xs font-medium text-gray-700 mb-1">{t('scanner.label_name')}</label>
        <input bind:value={newProd.name} placeholder={t('scanner.placeholder_name')}
          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
      </div>
      <div>
        <label class="block text-xs font-medium text-gray-700 mb-1">{t('scanner.label_vendor')}</label>
        <input bind:value={newProd.vendor} placeholder={t('scanner.placeholder_vendor')}
          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
      </div>
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1">{t('scanner.label_unit')}</label>
          <select bind:value={newProd.unit_id}
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
            <option value="">{t('scanner.unit_placeholder')}</option>
            {#each units as u}
              <option value={u.id}>{u.name} ({u.abbreviation})</option>
            {/each}
          </select>
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1">{t('scanner.label_category')}</label>
          <select bind:value={newProd.category_id}
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
            <option value="">{t('common.no_category')}</option>
            {#each categories as c}
              <option value={c.id}>{c.name}</option>
            {/each}
          </select>
        </div>
      </div>
      {#if newProd.unit_id}
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-2">{t('products.puc_label')}</label>
          <UnitConversionEditor
            conversions={newProd.puc}
            units={units}
            pucUnits={newProd.puc}
            withName={true}
            onadd={addNewProdPuc}
            onremove={removeNewProdPuc} />
        </div>
      {/if}
      <div class="flex justify-end gap-2">
        <button onclick={() => newProductModal = null}
          class="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">{t('common.cancel')}</button>
        <button onclick={createNewProduct}
          class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium">
          {t('scanner.btn_create_product')}
        </button>
      </div>
    </div>
  </Modal>
{/if}

<!-- Add Entry Modal -->
{#if addEntryModal}
  <StockEntryModal
    {products}
    {vaults}
    {units}
    initial={addEntryModal.product
      ? { product_id: addEntryModal.product.id, entry_unit_id: addEntryModal.product.entry_unit_key || 'base' }
      : { stock_id: addEntryModal.stockId }}
    productLocked={!!addEntryModal.product}
    isNew={true}
    autoPrintEnabled={getSetting('label_auto_print') === '1'}
    onsave={createEntry}
    onclose={() => addEntryModal = null} />
{/if}
