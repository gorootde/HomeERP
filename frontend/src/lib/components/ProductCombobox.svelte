<script>
  import { Search, X } from 'lucide-svelte';
  import { t } from '$lib/i18n.svelte.js';
  import { fmtProductLabel } from '$lib/utils.js';

  /**
   * Searchable product picker. Full-text filter over product name, vendor and
   * every EAN code, matching each whitespace-separated token as a case-insensitive
   * substring. `value` holds the selected product id (number) or '' — the same
   * shape the old <select> produced, so callers need no other changes.
   *
   * Props:
   *   products    — full product list ({ id, name, vendor, ean_codes: [{ code }] })
   *   value       — bindable selected product id (number) or ''
   *   placeholder — input placeholder
   *   disabled    — optional; renders the field read-only
   */
  let { products = [], value = $bindable(''), placeholder = '', disabled = false } = $props();

  const MAX_RESULTS = 50;

  let open = $state(false);
  let query = $state('');
  let highlight = $state(0);
  let rootEl;
  let inputEl;

  let selected = $derived(products.find((p) => p.id === Number(value)) || null);

  // While open the input shows the live query; when closed it shows the label of
  // the current selection.
  let display = $derived(open ? query : selected ? fmtProductLabel(selected) : '');

  let matches = $derived.by(() => {
    const tokens = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
    const hits = [];
    for (const p of products) {
      const haystacks = [
        (p.name || '').toLowerCase(),
        (p.vendor || '').toLowerCase(),
        ...(p.ean_codes || []).map((e) => (e.code || '').toLowerCase())
      ];
      if (tokens.every((tok) => haystacks.some((h) => h.includes(tok)))) {
        hits.push(p);
        if (hits.length >= MAX_RESULTS) break;
      }
    }
    return hits;
  });

  function openList() {
    if (disabled) return;
    open = true;
    query = selected ? fmtProductLabel(selected) : '';
    highlight = 0;
    queueMicrotask(() => inputEl?.select());
  }

  function choose(p) {
    value = p.id;
    open = false;
    query = '';
    inputEl?.blur();
  }

  function clear() {
    value = '';
    query = '';
    open = false;
    inputEl?.focus();
  }

  function onInput(e) {
    query = e.currentTarget.value;
    open = true;
    highlight = 0;
  }

  function onKeydown(e) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (!open) return openList();
      highlight = Math.min(highlight + 1, matches.length - 1);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      highlight = Math.max(highlight - 1, 0);
    } else if (e.key === 'Enter') {
      if (open && matches[highlight]) {
        e.preventDefault();
        choose(matches[highlight]);
      }
    } else if (e.key === 'Escape') {
      if (open) {
        e.stopPropagation();
        open = false;
        query = '';
      }
    }
  }

  $effect(() => {
    function onDocClick(e) {
      if (rootEl && !rootEl.contains(e.target)) {
        open = false;
        query = '';
      }
    }
    document.addEventListener('click', onDocClick, true);
    return () => document.removeEventListener('click', onDocClick, true);
  });
</script>

<div class="relative" bind:this={rootEl}>
  <Search size={16} class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
  <input
    bind:this={inputEl}
    type="text"
    role="combobox"
    aria-expanded={open}
    aria-autocomplete="list"
    autocomplete="off"
    {disabled}
    {placeholder}
    value={display}
    onfocus={openList}
    oninput={onInput}
    onkeydown={onKeydown}
    class="w-full min-w-0 pl-9 pr-9 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-500" />
  {#if value && !disabled}
    <button
      type="button"
      onclick={clear}
      tabindex="-1"
      aria-label={t('stock.clear_product')}
      title={t('stock.clear_product')}
      class="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-gray-700">
      <X size={14} />
    </button>
  {/if}

  {#if open}
    <ul
      role="listbox"
      class="absolute z-10 mt-1 w-full max-h-60 overflow-auto bg-white border border-gray-200 rounded-lg shadow-lg py-1 text-sm">
      {#if matches.length === 0}
        <li class="px-3 py-2 text-gray-400">{t('stock.no_product_match')}</li>
      {:else}
        {#each matches as p, i (p.id)}
          <button
            type="button"
            role="option"
            aria-selected={p.id === Number(value)}
            onclick={() => choose(p)}
            onmousemove={() => (highlight = i)}
            class={`block w-full text-left px-3 py-1.5 ${i === highlight ? 'bg-blue-50' : ''}`}>
            <span class={`block text-gray-900 ${p.id === Number(value) ? 'font-semibold' : ''}`}>
              {fmtProductLabel(p)}
            </span>
            {#if p.ean_codes?.length}
              <span class="block text-xs text-gray-400">{p.ean_codes.map((e) => e.code).join(', ')}</span>
            {/if}
          </button>
        {/each}
      {/if}
    </ul>
  {/if}
</div>
