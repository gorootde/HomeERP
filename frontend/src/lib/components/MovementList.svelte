<script>
  import { t } from '$lib/i18n.js';
  import { fmtQty, fmtDateTime } from '$lib/utils.js';
  import { Undo2 } from 'lucide-svelte';

  /**
   * Props:
   *   movements   — array of StockMovementRead
   *   showContext — include product / vault columns (list view); false for a single-entry modal
   *   onundo(id)  — called when the undo button of a row is clicked
   *   busyId      — id of the row currently being undone (disables its button)
   */
  let { movements = [], showContext = true, onundo, busyId = null } = $props();

  const reasonStyles = {
    create:  'bg-green-100 text-green-700',
    edit:    'bg-gray-100 text-gray-600',
    consume: 'bg-blue-100 text-blue-700',
    adjust:  'bg-amber-100 text-amber-700',
    delete:  'bg-red-100 text-red-700',
    undo:    'bg-purple-100 text-purple-700',
    import:  'bg-gray-100 text-gray-600'
  };

  function reasonLabel(r) {
    return t(`history.reason_${r}`) === `history.reason_${r}` ? r : t(`history.reason_${r}`);
  }
</script>

<div class="overflow-x-auto">
  <table class="w-full text-sm">
    <thead>
      <tr class="border-b border-gray-200 bg-gray-50">
        <th class="text-left px-3 py-2 text-xs font-semibold text-gray-500">{t('history.col_time')}</th>
        {#if showContext}
          <th class="text-left px-3 py-2 text-xs font-semibold text-gray-500">{t('history.col_product')}</th>
          <th class="text-left px-3 py-2 text-xs font-semibold text-gray-500 hidden sm:table-cell">{t('history.col_vault')}</th>
        {/if}
        <th class="text-right px-3 py-2 text-xs font-semibold text-gray-500">{t('history.col_change')}</th>
        <th class="text-right px-3 py-2 text-xs font-semibold text-gray-500 hidden md:table-cell">{t('history.col_result')}</th>
        <th class="text-left px-3 py-2 text-xs font-semibold text-gray-500">{t('history.col_reason')}</th>
        <th class="text-left px-3 py-2 text-xs font-semibold text-gray-500 hidden lg:table-cell">{t('history.col_note')}</th>
        <th class="px-3 py-2"></th>
      </tr>
    </thead>
    <tbody class="divide-y divide-gray-100">
      {#each movements as m}
        <tr class="hover:bg-gray-50 {m.undone ? 'opacity-50' : ''}">
          <td class="px-3 py-2 text-gray-500 whitespace-nowrap">{fmtDateTime(m.created_at)}</td>
          {#if showContext}
            <td class="px-3 py-2 font-medium text-gray-900">{m.product_name || '—'}</td>
            <td class="px-3 py-2 text-gray-600 hidden sm:table-cell">{m.vault_description || '—'}</td>
          {/if}
          <td class="px-3 py-2 text-right font-semibold tabular-nums {m.delta < 0 ? 'text-red-600' : 'text-green-600'}">
            {m.delta > 0 ? '+' : ''}{fmtQty(m.delta)} {m.unit?.abbreviation || ''}
          </td>
          <td class="px-3 py-2 text-right text-gray-500 tabular-nums hidden md:table-cell">
            {fmtQty(m.quantity_before)} → {fmtQty(m.quantity_after)}
          </td>
          <td class="px-3 py-2">
            <span class="text-xs font-medium rounded-full px-2 py-0.5 {reasonStyles[m.reason] || 'bg-gray-100 text-gray-600'}">
              {reasonLabel(m.reason)}
            </span>
            {#if m.undone}
              <span class="block text-[10px] text-gray-400 mt-0.5">{t('history.undone_badge')}</span>
            {/if}
          </td>
          <td class="px-3 py-2 text-gray-500 hidden lg:table-cell">{m.note || '—'}</td>
          <td class="px-3 py-2 text-right">
            {#if m.can_undo && onundo}
              <button onclick={() => onundo(m.id)} disabled={busyId === m.id}
                title={t('history.btn_undo')}
                class="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-lg border border-gray-300
                  text-gray-600 hover:bg-gray-100 disabled:opacity-50">
                <Undo2 size={13} /> {t('history.btn_undo')}
              </button>
            {/if}
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>
