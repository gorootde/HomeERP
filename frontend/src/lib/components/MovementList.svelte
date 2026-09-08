<script>
  import { t } from '$lib/i18n.svelte.js';
  import { fmtQty, fmtDateTime } from '$lib/utils.js';
  import DataTable from './DataTable.svelte';
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
    consume: 'bg-indigo-100 text-indigo-700',
    adjust:  'bg-amber-100 text-amber-700',
    delete:  'bg-red-100 text-red-700',
    undo:    'bg-purple-100 text-purple-700',
    import:  'bg-gray-100 text-gray-600'
  };

  function reasonLabel(r) {
    return t(`history.reason_${r}`) === `history.reason_${r}` ? r : t(`history.reason_${r}`);
  }
</script>

{#snippet timeCell(m)}<span class="text-gray-500 whitespace-nowrap">{fmtDateTime(m.created_at)}</span>{/snippet}
{#snippet productCell(m)}<span class="font-medium text-gray-900">{m.product_name || '—'}</span>{/snippet}
{#snippet vaultCell(m)}<span class="text-gray-600">{m.vault_description || '—'}</span>{/snippet}
{#snippet changeCell(m)}
  <span class="font-semibold tabular-nums {m.delta < 0 ? 'text-red-600' : 'text-green-600'}">
    {m.delta > 0 ? '+' : ''}{fmtQty(m.delta)} {m.unit?.abbreviation || ''}
  </span>
{/snippet}
{#snippet resultCell(m)}
  <span class="text-gray-500 tabular-nums">{fmtQty(m.quantity_before)} → {fmtQty(m.quantity_after)}</span>
{/snippet}
{#snippet reasonCell(m)}
  <span class="text-xs font-medium rounded-full px-2 py-0.5 {reasonStyles[m.reason] || 'bg-gray-100 text-gray-600'}">
    {reasonLabel(m.reason)}
  </span>
  {#if m.undone}
    <span class="block text-[10px] text-gray-400 mt-0.5">{t('history.undone_badge')}</span>
  {/if}
{/snippet}
{#snippet noteCell(m)}<span class="text-gray-500">{m.note || '—'}</span>{/snippet}
{#snippet actionsCell(m)}
  {#if m.can_undo && onundo}
    <button onclick={() => onundo(m.id)} disabled={busyId === m.id}
      title={t('history.btn_undo')}
      class="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-lg border border-gray-300
        text-gray-600 hover:bg-gray-100 disabled:opacity-50">
      <Undo2 size={13} /> {t('history.btn_undo')}
    </button>
  {/if}
{/snippet}

<DataTable
  dense
  rows={movements}
  rowKey={(m) => m.id}
  rowClass={(m) => m.undone ? 'opacity-50' : ''}
  actions={actionsCell}
  columns={[
    { key: 'time', label: t('history.col_time'), sortable: true, value: (m) => m.created_at, cell: timeCell },
    ...(showContext ? [
      { key: 'product', label: t('history.col_product'), sortable: true, value: (m) => m.product_name, cell: productCell },
      { key: 'vault', label: t('history.col_vault'), hideBelow: 'sm', sortable: true, value: (m) => m.vault_description, cell: vaultCell },
    ] : []),
    { key: 'change', label: t('history.col_change'), align: 'right', sortable: true, value: (m) => m.delta, cell: changeCell },
    { key: 'result', label: t('history.col_result'), align: 'right', hideBelow: 'md', cell: resultCell },
    { key: 'reason', label: t('history.col_reason'), sortable: true, value: (m) => m.reason, cell: reasonCell },
    { key: 'note', label: t('history.col_note'), hideBelow: 'lg', cell: noteCell },
  ]} />
