<script>
  import { onMount } from 'svelte';
  import { t } from '$lib/i18n.svelte.js';
  import { showToast } from '$lib/toast.js';
  import {
    getStockMovements, undoStockMovement, getConsumptionForecast,
    getVaults, getProducts
  } from '$lib/api.js';
  import { fmtQty, fmtDate, fmtProductLabel } from '$lib/utils.js';
  import MovementList from '$lib/components/MovementList.svelte';
  import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
  import FilterSelect from '$lib/components/FilterSelect.svelte';
  import { History, TrendingDown } from 'lucide-svelte';

  let movements = $state([]);
  let forecast = $state([]);
  let products = $state([]);
  let vaults = $state([]);
  let loading = $state(true);
  let undoBusyId = $state(null);
  let confirmUndo = $state(null);

  let filterProduct = $state('');
  let filterVault = $state('');
  let filterReason = $state('');
  let showUndone = $state(false);
  let forecastDays = $state('90');

  const reasons = ['create', 'edit', 'consume', 'adjust', 'delete', 'undo', 'import'];

  onMount(async () => {
    [products, vaults] = await Promise.all([getProducts('', 500), getVaults()]);
    await reload();
  });

  async function reload() {
    loading = true;
    try {
      const params = { include_undone: showUndone };
      if (filterProduct) params.product_id = filterProduct;
      if (filterVault) params.vault_id = filterVault;
      if (filterReason) params.reason = filterReason;
      [movements, forecast] = await Promise.all([
        getStockMovements(params),
        getConsumptionForecast({ days: forecastDays })
      ]);
    } finally {
      loading = false;
    }
  }

  async function doUndo() {
    const id = confirmUndo.id;
    confirmUndo = null;
    undoBusyId = id;
    try {
      await undoStockMovement(id);
      showToast(t('history.toast_undone'), 'success');
      await reload();
    } catch (e) {
      showToast(String(e), 'error');
    } finally {
      undoBusyId = null;
    }
  }
</script>

<div class="px-4 md:px-6 py-5 max-w-6xl">
  <div class="flex items-center gap-2 mb-1">
    <History size={20} class="text-gray-700" />
    <h1 class="text-xl font-bold text-gray-900">{t('history.title')}</h1>
  </div>
  <p class="text-sm text-gray-500 mb-4">{t('history.subtitle')}</p>

  <!-- Forecast -->
  <div class="bg-white rounded-xl border border-gray-200 mb-6">
    <div class="flex flex-wrap items-center gap-3 px-4 py-3 border-b border-gray-100">
      <div class="flex items-center gap-2 flex-1">
        <TrendingDown size={16} class="text-gray-500" />
        <h2 class="text-sm font-semibold text-gray-700">{t('forecast.title')}</h2>
      </div>
      <label class="text-xs text-gray-500">{t('forecast.window_label')}</label>
      <select bind:value={forecastDays} onchange={reload}
        class="px-2 py-1 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
        <option value="30">{t('forecast.window_30d')}</option>
        <option value="90">{t('forecast.window_90d')}</option>
        <option value="365">{t('forecast.window_365d')}</option>
      </select>
    </div>
    {#if forecast.length === 0}
      <p class="text-sm text-gray-400 px-4 py-6 text-center">{t('forecast.empty')}</p>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-gray-200 bg-gray-50">
              <th class="text-left px-4 py-2 text-xs font-semibold text-gray-500">{t('forecast.col_product')}</th>
              <th class="text-right px-4 py-2 text-xs font-semibold text-gray-500">{t('forecast.col_stock')}</th>
              <th class="text-right px-4 py-2 text-xs font-semibold text-gray-500">{t('forecast.col_rate')}</th>
              <th class="text-right px-4 py-2 text-xs font-semibold text-gray-500">{t('forecast.col_days_left')}</th>
              <th class="text-left px-4 py-2 text-xs font-semibold text-gray-500 hidden sm:table-cell">{t('forecast.col_until')}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            {#each forecast as f}
              {@const days = f.days_remaining == null ? null : Math.round(f.days_remaining)}
              <tr class="hover:bg-gray-50">
                <td class="px-4 py-2 font-medium text-gray-900">{f.product_name}</td>
                <td class="px-4 py-2 text-right tabular-nums text-gray-700">{fmtQty(f.current_stock)} {f.unit?.abbreviation || ''}</td>
                <td class="px-4 py-2 text-right tabular-nums text-gray-500">{fmtQty(f.avg_daily_consumption)} {f.unit?.abbreviation || ''}</td>
                <td class="px-4 py-2 text-right tabular-nums font-semibold {days != null && days <= 14 ? 'text-red-600' : days != null && days <= 30 ? 'text-amber-600' : 'text-gray-800'}">
                  {days == null ? t('forecast.na') : t('forecast.days_value', { days })}
                </td>
                <td class="px-4 py-2 text-gray-500 hidden sm:table-cell">{f.depletion_date ? fmtDate(f.depletion_date) : t('forecast.na')}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>

  <!-- Filters -->
  <div class="flex flex-wrap gap-2 mb-4">
    <FilterSelect bind:value={filterProduct} onchange={reload} placeholder={t('history.filter_all_products')}
      options={products.map(p => ({ value: p.id, label: fmtProductLabel(p) }))} />
    <FilterSelect bind:value={filterVault} onchange={reload} placeholder={t('history.filter_all_vaults')}
      options={vaults.map(v => ({ value: v.id, label: v.description }))} />
    <FilterSelect bind:value={filterReason} onchange={reload} placeholder={t('history.filter_all_reasons')}
      options={reasons.map(r => ({ value: r, label: t(`history.reason_${r}`) }))} />
    <label class="flex items-center gap-2 text-sm text-gray-600 px-2">
      <input type="checkbox" bind:checked={showUndone} onchange={reload} />
      {t('history.show_undone')}
    </label>
  </div>

  {#if loading}
    <div class="flex justify-center py-16 text-gray-400">{t('common.loading')}</div>
  {:else if movements.length === 0}
    <p class="text-center text-gray-400 py-12">{t('history.empty')}</p>
  {:else}
    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <MovementList {movements} showContext={true}
        busyId={undoBusyId}
        onundo={(id) => confirmUndo = { id }} />
    </div>
  {/if}
</div>

{#if confirmUndo}
  <ConfirmDialog
    message={t('history.confirm_undo')}
    confirmLabel={t('history.btn_undo')}
    onconfirm={doUndo}
    oncancel={() => confirmUndo = null} />
{/if}
