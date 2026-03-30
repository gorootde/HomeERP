<script>
  import { onMount } from 'svelte';
  import { t } from '$lib/i18n.js';
  import { getStockSummary, getCategoryStockSummary } from '$lib/api.js';
  import { fmtQty, trafficStatus } from '$lib/utils.js';
  import { Package, BarChart3, Warehouse, AlertTriangle } from 'lucide-svelte';

  let summary = $state([]);
  let catSummary = $state([]);
  let loading = $state(true);

  onMount(async () => {
    try {
      [summary, catSummary] = await Promise.all([getStockSummary(), getCategoryStockSummary()]);
    } finally {
      loading = false;
    }
  });

  let totalProducts = $derived(summary.length);
  let totalQty = $derived(summary.reduce((s, e) => s + (e.total_quantity || 0), 0));
  let vaultSet = $derived(new Set(summary.flatMap(e => (e.by_vault || []).map(v => v.vault_id))));
  let criticalCount = $derived(catSummary.filter(c => trafficStatus(c.total_quantity, c.min_stock_quantity) === 'critical').length);
  let lowCount = $derived(catSummary.filter(c => trafficStatus(c.total_quantity, c.min_stock_quantity) === 'low').length);

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
    <div class="flex justify-center py-16 text-gray-400">Loading…</div>
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
    {#if catSummary.length > 0}
      <h2 class="text-sm font-semibold text-gray-700 mb-3">{t('dashboard.section_by_category')}</h2>
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 mb-6">
        {#each catSummary as cat}
          {@const st = trafficStatus(cat.total_quantity, cat.min_stock_quantity)}
          <div class={`rounded-xl border p-3 ${statusColors[st]}`}>
            <div class="flex items-center justify-between mb-1">
              <span class="text-sm font-semibold text-gray-900 truncate">{cat.category_name}</span>
              <div class={`w-2.5 h-2.5 rounded-full shrink-0 ${statusBadgeColors[st]}`}></div>
            </div>
            <p class="text-lg font-bold text-gray-900">{fmtQty(cat.total_quantity)} {cat.min_stock_unit?.abbreviation || ''}</p>
            {#if cat.min_stock_quantity}
              <p class="text-xs {statusTextColors[st]}">
                Min: {fmtQty(cat.min_stock_quantity)} {cat.min_stock_unit?.abbreviation || ''}
              </p>
            {/if}
          </div>
        {/each}
      </div>
    {/if}

    <!-- All products table -->
    <h2 class="text-sm font-semibold text-gray-700 mb-3">{t('dashboard.section_all_products')}</h2>
    {#if summary.length === 0}
      <p class="text-gray-400 text-sm text-center py-8">{t('dashboard.empty')}</p>
    {:else}
      <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-gray-200 bg-gray-50">
                <th class="text-left px-4 py-2.5 text-xs font-semibold text-gray-500">{t('dashboard.col_product')}</th>
                <th class="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 hidden sm:table-cell">{t('dashboard.col_vendor')}</th>
                <th class="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 hidden sm:table-cell">{t('dashboard.col_size')}</th>
                <th class="text-right px-4 py-2.5 text-xs font-semibold text-gray-500">{t('dashboard.col_total_qty')}</th>
                <th class="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 hidden md:table-cell">{t('dashboard.col_by_vault')}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              {#each summary as row}
                <tr class="hover:bg-gray-50">
                  <td class="px-4 py-2.5 font-medium text-gray-900">{row.product_name}</td>
                  <td class="px-4 py-2.5 text-gray-500 hidden sm:table-cell">{row.vendor || '—'}</td>
                  <td class="px-4 py-2.5 text-gray-500 hidden sm:table-cell">{row.size || '—'}</td>
                  <td class="px-4 py-2.5 text-right font-semibold text-gray-900">
                    {fmtQty(row.total_quantity)} {row.unit?.abbreviation || ''}
                  </td>
                  <td class="px-4 py-2.5 hidden md:table-cell">
                    <div class="flex flex-wrap gap-1">
                      {#each row.by_vault || [] as bv}
                        <span class="text-xs bg-gray-100 text-gray-600 rounded-md px-1.5 py-0.5">
                          {bv.vault_description}: {fmtQty(bv.total_quantity)}
                        </span>
                      {/each}
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
