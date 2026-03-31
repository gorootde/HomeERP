<script>
  /**
   * Reusable unit conversion editor.
   *
   * Props:
   *   conversions    — Array of existing conversion objects
   *   units          — Array of selectable global target units
   *   pucUnits       — (optional) Array of product-specific conversions to offer as
   *                    additional target units (shown in a separate optgroup).
   *                    Their select value will be prefixed with "puc_" so the caller
   *                    can detect and resolve the chain (factor × puc.factor → base unit).
   *   fromAbbr       — Abbreviation of the "from" unit (used for preview, optional)
   *   withName       — Boolean: show a name field per conversion (product-specific mode)
   *   onadd(data)    — Called with { factor, to_unit_id, name? }
   *                    to_unit_id is either a number (global unit) or "puc_<id>" (product conv.)
   *   onremove(id)   — Called with conversion id when user clicks ✕
   */
  import { t } from '$lib/i18n.js';
  import { fmtFactor } from '$lib/utils.js';
  import { X, Plus } from 'lucide-svelte';

  let { conversions = [], units = [], pucUnits = [], fromAbbr = '', withName = false, onadd, onremove } = $props();

  let factor = $state('');
  let toUnitId = $state('');
  let name = $state('');

  let preview = $derived(() => {
    if (!factor || !toUnitId || !fromAbbr) return '';
    const globalUnit = units.find(u => String(u.id) === String(toUnitId));
    if (globalUnit) {
      return t('units.conv_preview', { from: fromAbbr, factor, to: globalUnit.abbreviation });
    }
    if (String(toUnitId).startsWith('puc_')) {
      const puc = pucUnits.find(c => 'puc_' + c.id === String(toUnitId));
      if (puc) return t('units.conv_preview', { from: fromAbbr, factor, to: puc.name });
    }
    return '';
  });

  function handleAdd() {
    const f = parseFloat(factor);
    if (!f || isNaN(f)) return;
    if (!toUnitId) return;
    onadd?.({ factor: f, to_unit_id: toUnitId, ...(withName ? { name } : {}) });
    factor = '';
    toUnitId = '';
    name = '';
  }

  function keydown(e) {
    if (e.key === 'Enter') { e.preventDefault(); handleAdd(); }
  }

  let hasAnyUnits = $derived(units.length > 0 || pucUnits.length > 0);
</script>

<div class="space-y-2">
  <!-- Existing conversions -->
  {#if conversions.length === 0}
    <p class="text-xs text-gray-400">{t('units.conv_empty')}</p>
  {:else}
    <div class="space-y-1">
      {#each conversions as conv}
        <div class="flex items-center gap-2 text-xs bg-gray-50 rounded-lg px-3 py-1.5">
          {#if withName && conv.name}
            <span class="font-medium text-gray-800 shrink-0">{conv.name}</span>
            <span class="text-gray-400">·</span>
          {/if}
          <span class="flex-1 text-gray-600">
            {#if fromAbbr}
              1 {fromAbbr} = {fmtFactor(conv.factor)} {conv.to_unit?.abbreviation}
            {:else}
              {fmtFactor(conv.factor)} × {conv.to_unit?.abbreviation}
            {/if}
          </span>
          <button onclick={() => onremove?.(conv.id)}
            class="text-red-400 hover:text-red-600 shrink-0">
            <X size={12} />
          </button>
        </div>
      {/each}
    </div>
  {/if}

  <!-- Add row -->
  {#if !hasAnyUnits}
    <p class="text-xs text-gray-400">{t('units.conv_no_other_units')}</p>
  {:else}
    <div class="flex gap-1.5 flex-wrap">
      {#if withName}
        <input bind:value={name} onkeydown={keydown}
          placeholder={t('products.puc_name_placeholder')}
          class="flex-1 min-w-24 px-2 py-1.5 text-xs border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500" />
      {/if}
      <input bind:value={factor} onkeydown={keydown} type="number" step="any"
        placeholder={t('units.conv_placeholder_factor')}
        class="w-20 px-2 py-1.5 text-xs border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500" />
      <select bind:value={toUnitId}
        class="flex-1 min-w-28 px-2 py-1.5 text-xs border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500">
        <option value="">{t('common.unit_placeholder')}</option>
        {#if units.length > 0}
          {#if pucUnits.length > 0}
            <optgroup label="Einheiten">
              {#each units as u}
                <option value={u.id}>{u.name} ({u.abbreviation})</option>
              {/each}
            </optgroup>
          {:else}
            {#each units as u}
              <option value={u.id}>{u.name} ({u.abbreviation})</option>
            {/each}
          {/if}
        {/if}
        {#if pucUnits.length > 0}
          <optgroup label="Produkteinheiten">
            {#each pucUnits as puc}
              <option value={'puc_' + puc.id}>{puc.name}</option>
            {/each}
          </optgroup>
        {/if}
      </select>
      <button onclick={handleAdd}
        class="px-3 py-1.5 text-xs bg-gray-800 text-white rounded-lg hover:bg-gray-700 flex items-center gap-1">
        <Plus size={12} /> {t('units.conv_btn_add')}
      </button>
    </div>
    {#if preview()}
      <p class="text-xs text-blue-600">{preview()}</p>
    {/if}
  {/if}
</div>
