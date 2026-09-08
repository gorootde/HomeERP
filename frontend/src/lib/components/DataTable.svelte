<script>
  /**
   * The one table component every data list uses. Wraps `ResponsiveTable` with:
   *   - 3-state column sorting (asc -> desc -> off, off = incoming order)
   *   - a filter bar built from column defs (reuses FilterSelect / SearchInput)
   *   - an optional global search box
   *   - a trailing right-aligned actions column
   *
   * Props:
   *   rows              — row data
   *   columns           — ColumnDef[]; see below
   *   rowKey(row)        — {#each} key, passed through
   *   rowClass(row)      — extra <tr> classes, passed through
   *   dense             — tighter padding, passed through
   *   search            — false | true (substring over every column with `value`)
   *                       | (row, query) => boolean predicate
   *   searchPlaceholder — search box placeholder (default t('common.table_search'))
   *   actions           — Snippet<[row]> rendered as the last column
   *   empty             — Snippet<[{ filtered: boolean }]> shown when 0 rows are visible
   *   card              — wrap the table (not the filter bar / not the empty state) in
   *                       the standard `bg-white rounded-xl border` card
   *
   * ColumnDef:
   *   key            — string identity; required for sortable / filter / hidden columns
   *   label          — header text; also the filter control's default aria-label
   *   align          — 'left' | 'right'
   *   hideBelow      — 'sm' | 'md' | 'lg' (table column only, never the filter control)
   *   hidden         — true: contributes only a filter control, no <th>/<td>
   *   cell           — Snippet<[row]>; required unless hidden
   *   value(row)     — accessor shared by sorting, `search: true` and shorthand filters
   *   sortable       — boolean
   *   sortValue(row) — optional sort override (defaults to value)
   *   filter         — 'text' | 'select' | { kind, options, placeholder?, match(row, v) }
   *   filterLabel    — aria-label override for the filter control
   */
  import { t } from '$lib/i18n.svelte.js';
  import { applyColumnFilters, applySearch, applySort, distinctOptions } from '$lib/datatable.js';
  import ResponsiveTable from './ResponsiveTable.svelte';
  import FilterSelect from './FilterSelect.svelte';
  import SearchInput from './SearchInput.svelte';

  let {
    rows = [], columns = [], rowKey, rowClass, dense = false,
    search = false, searchPlaceholder, actions, empty, card = false
  } = $props();

  let sortKey = $state(null);
  let sortDir = $state(null); // 'asc' | 'desc' | null
  let query = $state('');
  let filterValues = $state(
    Object.fromEntries(columns.filter((c) => c.filter).map((c) => [c.key, '']))
  );

  const filterColumns = $derived(columns.filter((c) => c.filter));
  const tableColumns = $derived(columns.filter((c) => !c.hidden));
  const mergedColumns = $derived(
    actions
      ? [...tableColumns, { key: '__actions', label: '', align: 'right', cell: actions }]
      : tableColumns
  );

  const anyFilterActive = $derived(
    (!!search && query.trim() !== '') ||
    filterColumns.some((c) => { const v = filterValues[c.key]; return v != null && v !== ''; })
  );

  const visibleRows = $derived.by(() => {
    let out = applyColumnFilters(filterColumns, rows, filterValues);
    out = applySearch(columns, out, search, query);
    out = applySort(out, columns, sortKey, sortDir);
    return out;
  });

  function toggleSort(key) {
    if (sortKey !== key) { sortKey = key; sortDir = 'asc'; }
    else if (sortDir === 'asc') sortDir = 'desc';
    else { sortKey = null; sortDir = null; }
  }

  const isTextFilter = (col) => col.filter === 'text' || col.filter?.kind === 'text';
  const optionsFor = (col) => col.filter?.options ?? distinctOptions(rows, col);
  const placeholderFor = (col) => col.filter?.placeholder ?? t('common.table_filter_all');
</script>

{#if search || filterColumns.length}
  <div class="flex flex-wrap items-center gap-2 mb-4">
    {#if search}
      <div class="flex-1 min-w-48">
        <SearchInput bind:value={query} placeholder={searchPlaceholder ?? t('common.table_search')} />
      </div>
    {/if}
    {#each filterColumns as col (col.key)}
      {#if isTextFilter(col)}
        <input bind:value={filterValues[col.key]} placeholder={placeholderFor(col)}
          aria-label={col.filterLabel ?? col.label}
          class="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" />
      {:else}
        <FilterSelect bind:value={filterValues[col.key]} options={optionsFor(col)}
          placeholder={placeholderFor(col)} aria-label={col.filterLabel ?? col.label} />
      {/if}
    {/each}
  </div>
{/if}

{#snippet table()}
  <ResponsiveTable rows={visibleRows} {rowKey} {rowClass} {dense}
    sortBy={sortKey} {sortDir} onSortToggle={toggleSort} columns={mergedColumns} />
{/snippet}

{#if visibleRows.length === 0 && empty}
  {@render empty({ filtered: anyFilterActive })}
{:else if card}
  <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
    {@render table()}
  </div>
{:else}
  {@render table()}
{/if}
