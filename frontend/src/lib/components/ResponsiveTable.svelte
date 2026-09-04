<script>
  /**
   * Data table with responsive column hiding, replacing the hand-rolled
   * `<table>`/`<thead>`/`<tbody>` + `hidden sm:table-cell` markup that used to
   * be duplicated across every list page. Each column's cell content is a
   * snippet, so pages keep full control over what a cell renders (composite
   * cells, chips, action buttons, ...).
   *
   * Props:
   *   columns — [{ label, align: 'left'|'right' (default 'left'),
   *                hideBelow: 'sm'|'md'|'lg' (default: always visible),
   *                cell: Snippet<[row]> }]
   *   rows    — row data
   *   rowKey(row)   — optional {#each} key function
   *   rowClass(row) — optional extra classes for a row's <tr>
   *   dense   — tighter padding (px-3 py-2 instead of px-4 py-2.5), for
   *             tables embedded in a modal rather than a full page section
   */
  let { columns = [], rows = [], rowKey, rowClass, dense = false } = $props();

  const hideClass = { sm: 'hidden sm:table-cell', md: 'hidden md:table-cell', lg: 'hidden lg:table-cell' };
  const pad = dense ? 'px-3 py-2' : 'px-4 py-2.5';
</script>

<div class="overflow-x-auto">
  <table class="w-full text-sm">
    <thead>
      <tr class="border-b border-gray-200 bg-gray-50">
        {#each columns as col}
          <th class="{pad} text-xs font-semibold text-gray-500 {col.align === 'right' ? 'text-right' : 'text-left'} {hideClass[col.hideBelow] || ''}">
            {col.label || ''}
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
