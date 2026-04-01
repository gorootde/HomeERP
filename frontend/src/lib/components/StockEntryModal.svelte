<script>
  import { t } from '$lib/i18n.js';
  import Modal from './Modal.svelte';
  import BarcodeScanner from './BarcodeScanner.svelte';
  import { ScanLine } from 'lucide-svelte';

  /**
   * Props:
   *   products      — full product list (for dropdown). Pass [product] when productLocked=true.
   *   vaults        — vault list
   *   units         — global units list (for entry-unit conversion options)
   *   initial       — initial form values { product_id, vault_id, quantity, entry_unit_id,
   *                   best_before_date, comment }
   *   productLocked — when true, product field is shown as readonly text (pre-selected)
   *   isNew         — controls modal title and save button label
   *   onsave(data)  — called with { product_id, vault_id, quantity, best_before_date, comment }
   *                   quantity is already converted to the product's base unit
   *   onclose()     — called on cancel / modal close
   */
  let {
    products = [],
    vaults = [],
    units = [],
    initial = {},
    productLocked = false,
    isNew = true,
    onsave,
    onclose
  } = $props();

  const LAST_VAULT_KEY = 'homeerp_last_vault_id';

  function loadLastVault() {
    try { return Number(localStorage.getItem(LAST_VAULT_KEY)) || ''; } catch { return ''; }
  }

  function saveLastVault(id) {
    try { if (id) localStorage.setItem(LAST_VAULT_KEY, String(id)); } catch {}
  }

  const defaultVaultId = initial.vault_id ?? loadLastVault();

  let form = $state({
    product_id:       initial.product_id      ?? '',
    vault_id:         defaultVaultId,
    quantity:         String(initial.quantity  ?? '1'),
    entry_unit_id:    initial.entry_unit_id    ?? 'base',
    best_before_date: initial.best_before_date ?? '',
    comment:          initial.comment          ?? '',
    stock_id:         ''
  });

  let stockIdScannerActive = $state(false);

  function handleStockIdScan(code) {
    form.stock_id = code;
    stockIdScannerActive = false;
  }

  // When product changes (only in unlocked mode), reset entry_unit_id to that product's default
  $effect(() => {
    if (productLocked) return;
    const product = products.find(p => p.id === Number(form.product_id));
    form.entry_unit_id = product?.entry_unit_key || (product?.size ? 'stueck' : 'base');
  });

  let entryUnits = $derived(() => {
    const product = products.find(p => p.id === Number(form.product_id));
    if (!product?.unit) return [];
    const baseUnitId = product.unit.id;
    const result = [{ id: 'base', label: product.unit.name, abbreviation: product.unit.abbreviation, factor: 1 }];
    if (product.size) {
      result.push({ id: 'stueck', label: 'Stück', abbreviation: 'Stk.', factor: product.size });
    }
    for (const puc of product.unit_conversions || []) {
      result.push({ id: 'puc_' + puc.id, label: puc.unit_name, abbreviation: puc.unit_name, factor: puc.factor });
    }
    for (const u of units) {
      if (u.id === baseUnitId) continue;
      const conv = (u.conversions || []).find(c => c.to_unit?.id === baseUnitId);
      if (conv) result.push({ id: 'global_' + u.id, label: u.name, abbreviation: u.abbreviation, factor: conv.factor });
    }
    return result;
  });

  let lockedProduct = $derived(products.find(p => p.id === Number(form.product_id)));

  function save() {
    const eu = entryUnits().find(u => u.id === form.entry_unit_id);
    const factor = eu?.factor ?? 1;
    saveLastVault(form.vault_id);
    onsave?.({
      product_id:      Number(form.product_id),
      vault_id:        Number(form.vault_id),
      quantity:        Number(form.quantity) * factor,
      best_before_date: form.best_before_date || null,
      comment:         form.comment || null,
      ...(isNew && form.stock_id ? { stock_id: form.stock_id } : {})
    });
  }
</script>

<Modal title={isNew ? t('stock.modal_add') : t('stock.modal_edit')} {onclose}>
  <div class="space-y-4">

    <!-- Product: readonly badge when locked, dropdown otherwise -->
    <div>
      <label class="block text-xs font-medium text-gray-700 mb-1">{t('stock.label_product')}</label>
      {#if productLocked}
        <div class="w-full px-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg text-gray-800">
          {lockedProduct?.name ?? '—'}
        </div>
      {:else}
        <select bind:value={form.product_id}
          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
          <option value="">{t('stock.select_product')}</option>
          {#each products as p}
            <option value={p.id}>{p.name}</option>
          {/each}
        </select>
      {/if}
    </div>

    <!-- Vault -->
    <div>
      <label class="block text-xs font-medium text-gray-700 mb-1">{t('stock.label_vault')}</label>
      <select bind:value={form.vault_id}
        class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
        <option value="">{t('stock.select_vault')}</option>
        {#each vaults as v}
          <option value={v.id}>{v.description}</option>
        {/each}
      </select>
    </div>

    <!-- Quantity + unit selector -->
    <div>
      <label class="block text-xs font-medium text-gray-700 mb-1">{t('stock.label_qty')}</label>
      <div class="flex gap-2">
        <div class="flex rounded-lg border border-gray-300 focus-within:ring-2 focus-within:ring-blue-500 overflow-hidden flex-1">
          <input bind:value={form.quantity} type="number" step="any"
            class="flex-1 px-3 py-2 text-sm focus:outline-none min-w-0" />
        </div>
        {#if entryUnits().length > 1}
          <select bind:value={form.entry_unit_id}
            class="px-2 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
            {#each entryUnits() as u}
              <option value={u.id}>{u.abbreviation}</option>
            {/each}
          </select>
        {:else if entryUnits().length === 1}
          <span class="px-3 py-2 text-sm text-gray-500 bg-gray-100 border border-gray-300 rounded-lg shrink-0 flex items-center">
            {entryUnits()[0].abbreviation}
          </span>
        {/if}
      </div>
    </div>

    <!-- Best before date -->
    <div>
      <label class="block text-xs font-medium text-gray-700 mb-1">{t('stock.label_bbd')}</label>
      <input bind:value={form.best_before_date} type="date"
        class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
    </div>

    <!-- Comment -->
    <div>
      <label class="block text-xs font-medium text-gray-700 mb-1">{t('stock.label_comment')}</label>
      <input bind:value={form.comment} placeholder={t('stock.placeholder_comment')}
        class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
    </div>

    <!-- Stock ID (only when creating new entry) -->
    {#if isNew}
    <div>
      <label class="block text-xs font-medium text-gray-700 mb-1">
        {t('stock.label_stock_id')}
        <span class="text-gray-400 font-normal ml-1">({t('common.optional')})</span>
      </label>
      {#if stockIdScannerActive}
        <BarcodeScanner active={true} onscan={handleStockIdScan} />
        <button type="button" onclick={() => stockIdScannerActive = false}
          class="w-full mt-1 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
          {t('stock.stockid_btn_stop')}
        </button>
      {:else}
        <div class="flex gap-2">
          <input bind:value={form.stock_id} placeholder={t('stock.placeholder_stock_id')}
            class="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono" />
          <button type="button" onclick={() => stockIdScannerActive = true}
            class="px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center gap-1.5">
            <ScanLine size={15} />
          </button>
        </div>
      {/if}
    </div>
    {/if}

    <div class="flex justify-end gap-2 pt-2 border-t border-gray-100">
      <button onclick={onclose}
        class="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
        {t('common.cancel')}
      </button>
      <button onclick={save}
        class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium">
        {isNew ? t('common.create') : t('common.save')}
      </button>
    </div>
  </div>
</Modal>
