<script>
  /**
   * Internal presentational table shell: responsive column hiding, right-align,
   * dense padding, per-cell snippets and (optional) sortable header buttons.
   * Pages don't use this directly — they use `DataTable.svelte`, which owns the
   * filter/sort/search state and renders through here.
   *
   * Props:
   *   columns — [{ key, label, align: 'left'|'right' (default 'left'),
   *                hideBelow: 'sm'|'md'|'lg' (default: always visible),
   *                sortable, cell: Snippet<[row]> }]
   *   rows    — row data
   *   rowKey(row)   — optional {#each} key function
   *   rowClass(row) — optional extra classes for a row's <tr>
   *   dense   — tighter padding (px-3 py-2 instead of px-4 py-2.5)
   *   sortBy / sortDir — active sort column key and 'asc'|'desc'|null
   *   onSortToggle(key) — click handler for a sortable header; enables the buttons
   */
  import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-svelte';
  import { t } from '$lib/i18n.svelte.js';

  let {
    columns = [], rows = [], rowKey, rowClass, dense = false,
    sortBy = null, sortDir = null, onSortToggle
  } = $props();

  const hideClass = { sm: 'hidden sm:table-cell', md: 'hidden md:table-cell', lg: 'hidden lg:table-cell' };
  const pad = dense ? 'px-3 py-2' : 'px-4 py-2.5';

  const ariaSort = (col) =>
    onSortToggle && col.sortable && sortBy === col.key
      ? (sortDir === 'asc' ? 'ascending' : sortDir === 'desc' ? 'descending' : undefined)
      : undefined;
</script>

<div class="overflow-x-auto">
  <table class="w-full text-sm">
    <thead>
      <tr class="border-b border-gray-200 bg-gray-50">
        {#each columns as col}
          <th aria-sort={ariaSort(col)}
            class="{pad} text-xs font-semibold text-gray-500 {col.align === 'right' ? 'text-right' : 'text-left'} {hideClass[col.hideBelow] || ''}">
            {#if onSortToggle && col.sortable}
              <button type="button" onclick={() => onSortToggle(col.key)}
                title={t('common.sort_by', { col: col.label || '' })}
                class="inline-flex items-center gap-1 font-semibold hover:text-gray-700 {col.align === 'right' ? 'flex-row-reverse' : ''}">
                {col.label || ''}
                {#if sortBy === col.key && sortDir === 'asc'}
                  <ChevronUp size={14} />
                {:else if sortBy === col.key && sortDir === 'desc'}
                  <ChevronDown size={14} />
                {:else}
                  <ChevronsUpDown size={14} class="text-gray-300" />
                {/if}
              </button>
            {:else}
              {col.label || ''}
            {/if}
          </th>
        {/each}
      </tr>
    </thead>
    <tbody class="divide-y divide-gray-100">
      {#each rows as row (rowKey ? rowKey(row) : row)}
        <tr class="hover:bg-gray-50 {rowClass?.(row) || ''}">
          {#each columns as col}
            <td class="{pad} {col.align === 'right' ? 'text-right' : ''} {hideClass[col.hideBelow] || ''}">
              {@render col.cell(row)}
            </td>
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
</div>
