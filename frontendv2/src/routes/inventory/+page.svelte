<script>
  import { onMount } from 'svelte';
  import { t } from '$lib/i18n.js';
  import { showToast } from '$lib/toast.js';
  import { getVaults, getStockEntries, updateStockEntry, getByEan } from '$lib/api.js';
  import { fmtQty } from '$lib/utils.js';
  import BarcodeScanner from '$lib/components/BarcodeScanner.svelte';

  // Steps: select | counting | result
  let step = $state('select');
  let vaults = $state([]);
  let selectedVaultId = $state('');
  let entries = $state([]); // expected entries for vault
  let scannerActive = $state(false);
  let feedback = $state('');

  // Counting state
  let scanned = $state({}); // productId -> count
  let unknownEans = $state([]);
  let scanCount = $state(0);

  // Result
  let results = $state([]);

  onMount(async () => {
    vaults = await getVaults();
  });

  async function startInventory() {
    if (!selectedVaultId) return;
    entries = await getStockEntries({ vault_id: selectedVaultId });
    scanned = {};
    unknownEans = [];
    scanCount = 0;
    feedback = t('inventory.feedback_initial');
    step = 'counting';
  }

  async function handleScan(code) {
    scanCount++;
    feedback = t('inventory.status_searching');
    try {
      const product = await getByEan(code);
      const productId = product.id;
      scanned[productId] = (scanned[productId] || 0) + 1;
      feedback = t('inventory.feedback_scanned', { name: product.name });
    } catch {
      if (!unknownEans.includes(code)) unknownEans = [...unknownEans, code];
      feedback = t('inventory.feedback_unknown_ean', { ean: code });
    }
  }

  function finishCounting() {
    scannerActive = false;
    // Build results
    const productMap = {};
    for (const e of entries) {
      if (!productMap[e.product_id]) {
        productMap[e.product_id] = { product: e.product, expected: 0, entryId: e.id };
      }
      productMap[e.product_id].expected += e.quantity;
    }

    const allProductIds = new Set([
      ...Object.keys(productMap).map(Number),
      ...Object.keys(scanned).map(Number)
    ]);

    results = [...allProductIds].map(pid => {
      const info = productMap[pid];
      const scannedQty = scanned[pid] || 0;
      const expectedQty = info?.expected || 0;
      const diff = scannedQty - expectedQty;
      let status;
      if (!info) status = 'unexpected';
      else if (diff === 0) status = 'ok';
      else if (diff < 0) status = 'missing';
      else status = 'extra';

      return {
        product: info?.product || { id: pid, name: `Product #${pid}` },
        entryId: info?.entryId,
        expected: expectedQty,
        scanned: scannedQty,
        diff,
        status
      };
    });

    step = 'result';
  }

  async function applyResult(row) {
    if (!row.entryId) return;
    try {
      const entry = entries.find(e => e.id === row.entryId);
      if (entry) {
        await updateStockEntry(row.entryId, { ...entry, quantity: row.scanned });
        showToast(t('inventory.toast_updated'), 'success');
        row.status = 'ok';
        row.expected = row.scanned;
        row.diff = 0;
        results = [...results];
      }
    } catch (e) {
      showToast(String(e), 'error');
    }
  }

  async function applyAll() {
    for (const row of results.filter(r => r.status !== 'ok' && r.entryId)) {
      await applyResult(row);
    }
    showToast(t('inventory.toast_applied'), 'success');
  }

  function reset() {
    step = 'select';
    selectedVaultId = '';
    results = [];
    scanned = {};
  }

  let productCount = $derived(Object.keys(scanned).length);
  let expectedCount = $derived(entries.length);

  const statusColors = {
    ok: 'text-green-600',
    missing: 'text-red-600',
    extra: 'text-yellow-600',
    unexpected: 'text-purple-600'
  };
  const statusBg = {
    ok: 'bg-green-50',
    missing: 'bg-red-50',
    extra: 'bg-yellow-50',
    unexpected: 'bg-purple-50'
  };
</script>

<div class="px-4 md:px-6 py-5 max-w-2xl">
  <h1 class="text-xl font-bold text-gray-900 mb-5">{t('inventory.title')}</h1>

  <!-- Step: Select Vault -->
  {#if step === 'select'}
    <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
      <h2 class="text-sm font-semibold text-gray-700">{t('inventory.step_select_heading')}</h2>
      <div>
        <label class="block text-xs font-medium text-gray-700 mb-1">{t('inventory.label_vault')}</label>
        <select bind:value={selectedVaultId}
          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
          <option value="">{t('inventory.select_vault')}</option>
          {#each vaults as v}
            <option value={v.id}>{v.description}</option>
          {/each}
        </select>
      </div>
      <button onclick={startInventory} disabled={!selectedVaultId}
        class="w-full py-2.5 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-40">
        {t('inventory.btn_start')}
      </button>
    </div>
  {/if}

  <!-- Step: Counting -->
  {#if step === 'counting'}
    <div class="space-y-4">
      <!-- Tally -->
      <div class="grid grid-cols-3 gap-3">
        <div class="bg-white rounded-xl border border-gray-200 p-3 text-center">
          <p class="text-2xl font-bold text-gray-900">{scanCount}</p>
          <p class="text-xs text-gray-500">{t('inventory.tally_scans')}</p>
        </div>
        <div class="bg-white rounded-xl border border-gray-200 p-3 text-center">
          <p class="text-2xl font-bold text-gray-900">{productCount}</p>
          <p class="text-xs text-gray-500">{t('inventory.tally_products')}</p>
        </div>
        <div class="bg-white rounded-xl border border-gray-200 p-3 text-center">
          <p class="text-2xl font-bold text-gray-900">{expectedCount}</p>
          <p class="text-xs text-gray-500">{t('inventory.tally_expected')}</p>
        </div>
      </div>

      <!-- Scanner -->
      <div class="bg-white rounded-xl border border-gray-200 p-4">
        <BarcodeScanner active={scannerActive} onscan={handleScan} />
        <p class="text-sm text-center text-gray-500 mt-2">{feedback}</p>
        <div class="flex gap-2 mt-3">
          <button onclick={() => scannerActive = !scannerActive}
            class="flex-1 py-2 text-sm font-medium rounded-lg border transition-colors
              {scannerActive ? 'bg-red-50 text-red-700 border-red-200' : 'bg-blue-600 text-white border-transparent hover:bg-blue-700'}">
            {scannerActive ? t('inventory.btn_stop_scanner') : t('inventory.btn_start_scanner')}
          </button>
          <button onclick={finishCounting}
            class="flex-1 py-2 text-sm font-medium bg-gray-800 text-white rounded-lg hover:bg-gray-700">
            {t('inventory.btn_finish')}
          </button>
        </div>
        <button onclick={reset} class="w-full mt-2 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
          {t('inventory.btn_cancel')}
        </button>
      </div>

      <!-- Unknown EANs -->
      {#if unknownEans.length > 0}
        <div class="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm">
          <p class="font-medium text-amber-800">{t('inventory.unknown_eans_prefix')}</p>
          <div class="flex flex-wrap gap-1 mt-1">
            {#each unknownEans as ean}
              <span class="font-mono text-xs bg-amber-100 text-amber-700 rounded px-1.5 py-0.5">{ean}</span>
            {/each}
          </div>
        </div>
      {/if}
    </div>
  {/if}

  <!-- Step: Result -->
  {#if step === 'result'}
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <h2 class="text-sm font-semibold text-gray-700">{t('inventory.result_title')}</h2>
        <div class="flex gap-2">
          <button onclick={applyAll}
            class="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            {t('inventory.btn_apply_all')}
          </button>
          <button onclick={reset}
            class="px-3 py-1.5 text-xs font-medium border border-gray-300 rounded-lg hover:bg-gray-50">
            {t('inventory.btn_new')}
          </button>
        </div>
      </div>

      {#if results.length === 0}
        <p class="text-center text-gray-400 py-8">{t('inventory.empty')}</p>
      {:else}
        <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-gray-200 bg-gray-50">
                  <th class="text-left px-4 py-2.5 text-xs font-semibold text-gray-500">{t('inventory.col_product')}</th>
                  <th class="text-right px-4 py-2.5 text-xs font-semibold text-gray-500">{t('inventory.col_expected')}</th>
                  <th class="text-right px-4 py-2.5 text-xs font-semibold text-gray-500">{t('inventory.col_scanned')}</th>
                  <th class="text-right px-4 py-2.5 text-xs font-semibold text-gray-500">{t('inventory.col_diff')}</th>
                  <th class="text-left px-4 py-2.5 text-xs font-semibold text-gray-500">{t('inventory.col_status')}</th>
                  <th class="px-4 py-2.5"></th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100">
                {#each results as row}
                  <tr class={row.status !== 'ok' ? statusBg[row.status] : ''}>
                    <td class="px-4 py-2.5 font-medium text-gray-900">{row.product?.name || '—'}</td>
                    <td class="px-4 py-2.5 text-right text-gray-600">{fmtQty(row.expected)}</td>
                    <td class="px-4 py-2.5 text-right text-gray-600">{fmtQty(row.scanned)}</td>
                    <td class="px-4 py-2.5 text-right font-medium {statusColors[row.status]}">
                      {row.diff > 0 ? '+' : ''}{fmtQty(row.diff)}
                    </td>
                    <td class="px-4 py-2.5">
                      <span class={`text-xs font-medium ${statusColors[row.status]}`}>
                        {t(`inventory.status_${row.status}`)}
                      </span>
                    </td>
                    <td class="px-4 py-2.5">
                      {#if row.status !== 'ok' && row.entryId}
                        <button onclick={() => applyResult(row)}
                          class="text-xs px-2.5 py-1 bg-blue-600 text-white rounded-md hover:bg-blue-700">
                          {t('inventory.btn_update_db')}
                        </button>
                      {/if}
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      {/if}

      <!-- Unknown EANs in result -->
      {#if unknownEans.length > 0}
        <div class="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm">
          <p class="font-medium text-amber-800">{t('inventory.unknown_eans_prefix')}</p>
          <div class="flex flex-wrap gap-1 mt-1">
            {#each unknownEans as ean}
              <span class="font-mono text-xs bg-amber-100 text-amber-700 rounded px-1.5 py-0.5">{ean}</span>
            {/each}
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div>
