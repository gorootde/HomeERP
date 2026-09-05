<script>
  import { onMount } from 'svelte';
  import { t } from '$lib/i18n.svelte.js';
  import { getStockSummary, getCategoryStockSummary, getConsumptionForecast } from '$lib/api.js';
  import { fmtQty, fmtDate, trafficStatus } from '$lib/utils.js';
  import ResponsiveTable from '$lib/components/ResponsiveTable.svelte';
  import { Package, BarChart3, Warehouse, AlertTriangle, TrendingDown } from 'lucide-svelte';

  let summary = $state([]);
  let catSummary = $state([]);
  let forecast = $state([]);
  let loading = $state(true);

  onMount(async () => {
    try {
      [summary, catSummary, forecast] = await Promise.all([
        getStockSummary(), getCategoryStockSummary(), getConsumptionForecast({ days: 90 })
      ]);
    } finally {
      loading = false;
    }
  });

  let runningLow = $derived(forecast.filter(f => f.days_remaining != null).slice(0, 6));

  // Categories without a minimum stock are not tracked on the dashboard.
  let trackedCats = $derived(catSummary.filter(c => c.min_stock_quantity != null));

  let totalProducts = $derived(summary.length);
  let totalQty = $derived(summary.reduce((s, e) => s + (e.total_quantity || 0), 0));
  let vaultSet = $derived(new Set(summary.flatMap(e => (e.by_vault || []).map(v => v.vault_id))));
  let criticalCount = $derived(trackedCats.filter(c => trafficStatus(c.total_quantity, c.min_stock_quantity) === 'critical').length);
  let lowCount = $derived(trackedCats.filter(c => trafficStatus(c.total_quantity, c.min_stock_quantity) === 'low').length);

  const statusColors = {
    ok: 'bg-green-100 border-green-300',
    low: 'bg-yellow-100 border-yellow-300',
    critical: 'bg-red-100 border-red-300',
    none: 'bg-gray-100 border-gray-200'
  };
  const statusTextColors = {
    ok: 'text-green-700', low: 'text-yellow-700', critical: 'text-red-700', none: 'text-gray-500'
  };
  const statusBadgeColors = {
    ok: 'bg-green-500', low: 'bg-yellow-400', critical: 'bg-red-500', none: 'bg-gray-300'
  };
</script>

<div class="px-4 md:px-6 py-5 max-w-5xl">
  <h1 class="text-xl font-bold text-gray-900 mb-5">{t('dashboard.title')}</h1>

  {#if loading}
    <div class="flex justify-center py-16 text-gray-400">{t('common.loading')}</div>
  {:else}
    <!-- Stats row -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
      <div class="bg-white rounded-xl border border-gray-200 p-4">
        <div class="flex items-center gap-2 text-gray-500 text-xs font-medium mb-1">
          <Package size={14} /> {t('dashboard.products_in_stock')}
        </div>
        <p class="text-2xl font-bold text-gray-900">{totalProducts}</p>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 p-4">
        <div class="flex items-center gap-2 text-gray-500 text-xs font-medium mb-1">
          <BarChart3 size={14} /> {t('dashboard.total_stock')}
        </div>
        <p class="text-2xl font-bold text-gray-900">{fmtQty(totalQty)}</p>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 p-4">
        <div class="flex items-center gap-2 text-gray-500 text-xs font-medium mb-1">
          <Warehouse size={14} /> {t('dashboard.storage_locations')}
        </div>
        <p class="text-2xl font-bold text-gray-900">{vaultSet.size}</p>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 p-4">
        <div class="flex items-center gap-2 text-gray-500 text-xs font-medium mb-1">
          <AlertTriangle size={14} /> {t('dashboard.critical')} / {t('dashboard.low')}
        </div>
        <p class="text-2xl font-bold text-gray-900">
          <span class="text-red-600">{criticalCount}</span>
          <span class="text-gray-400 text-lg"> / </span>
          <span class="text-yellow-600">{lowCount}</span>
        </p>
      </div>
    </div>

    <!-- Category cards -->
    {#if trackedCats.length > 0}
      <h2 class="text-sm font-semibold text-gray-700 mb-3">{t('dashboard.section_by_category')}</h2>
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 mb-6">
        {#each trackedCats as cat}
          {@const st = trafficStatus(cat.total_quantity, cat.min_stock_quantity)}
          <div class={`rounded-xl border p-3 ${statusColors[st]}`}>
            <div class="flex items-center justify-between mb-1">
              <span class="text-sm font-semibold text-gray-900 truncate">{cat.category_name}</span>
              <div class={`w-2.5 h-2.5 rounded-full shrink-0 ${statusBadgeColors[st]}`}></div>
            </div>
            <p class="text-lg font-bold text-gray-900">{fmtQty(cat.total_quantity)} {cat.min_stock_unit?.abbreviation || ''}</p>
            {#if cat.min_stock_quantity}
              <p class="text-xs {statusTextColors[st]}">
                {t('dashboard.min_prefix')} {fmtQty(cat.min_stock_quantity)} {cat.min_stock_unit?.abbreviation || ''}
              </p>
            {/if}
            {#if cat.unconverted_product_count > 0}
              <p class="text-xs text-gray-500 mt-0.5">
                {t('dashboard.unconverted_hint', { count: cat.unconverted_product_count })}
              </p>
            {/if}
          </div>
        {/each}
      </div>
    {/if}

    <!-- Consumption forecast -->
    {#if runningLow.length > 0}
      <div class="flex items-center gap-2 mb-1">
        <TrendingDown size={15} class="text-gray-500" />
        <h2 class="text-sm font-semibold text-gray-700">{t('forecast.dashboard_title')}</h2>
      </div>
      <p class="text-xs text-gray-400 mb-3">{t('forecast.dashboard_hint')}</p>
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
        {#each runningLow as f}
          {@const days = Math.round(f.days_remaining)}
          <a href="/history"
            class="rounded-xl border p-3 block hover:shadow-sm transition-shadow
              {days <= 14 ? 'bg-red-50 border-red-200' : days <= 30 ? 'bg-yellow-50 border-yellow-200' : 'bg-white border-gray-200'}">
            <p class="text-sm font-semibold text-gray-900 truncate">{f.product_name}</p>
            <p class="text-lg font-bold {days <= 14 ? 'text-red-600' : days <= 30 ? 'text-yellow-700' : 'text-gray-900'}">
              {t('forecast.days_value', { days })}
            </p>
            <p class="text-xs text-gray-500">
              {fmtQty(f.current_stock)} {f.unit?.abbreviation || ''}
              {#if f.depletion_date} · {fmtDate(f.depletion_date)}{/if}
            </p>
          </a>
        {/each}
      </div>
    {/if}

    <!-- All products table -->
    <h2 class="text-sm font-semibold text-gray-700 mb-3">{t('dashboard.section_all_products')}</h2>
    {#if summary.length === 0}
      <p class="text-gray-400 text-sm text-center py-8">{t('dashboard.empty')}</p>
    {:else}
      {#snippet nameCell(row)}<span class="font-medium text-gray-900">{row.product_name}</span>{/snippet}
      {#snippet vendorCell(row)}<span class="text-gray-500">{row.vendor || '—'}</span>{/snippet}
      {#snippet qtyCell(row)}
        <span class="font-semibold text-gray-900">{fmtQty(row.total_quantity)} {row.unit?.abbreviation || ''}</span>
      {/snippet}
      {#snippet byVaultCell(row)}
        <div class="flex flex-wrap gap-1">
          {#each row.by_vault || [] as bv}
            <span class="text-xs bg-gray-100 text-gray-600 rounded-md px-1.5 py-0.5">
              {bv.vault_description}: {fmtQty(bv.total_quantity)}
            </span>
          {/each}
        </div>
      {/snippet}
      <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <ResponsiveTable
          rows={summary}
          rowKey={(row) => row.product_id}
          columns={[
            { label: t('dashboard.col_product'), cell: nameCell },
            { label: t('dashboard.col_vendor'), hideBelow: 'sm', cell: vendorCell },
            { label: t('dashboard.col_total_qty'), align: 'right', cell: qtyCell },
            { label: t('dashboard.col_by_vault'), hideBelow: 'md', cell: byVaultCell },
          ]} />
      </div>
    {/if}
  {/if}
</div>
