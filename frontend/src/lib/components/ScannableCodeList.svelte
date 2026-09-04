<script>
  import { t } from '$lib/i18n.js';
  import BarcodeScanner from './BarcodeScanner.svelte';
  import { X, ScanLine } from 'lucide-svelte';

  /**
   * Chips + scanner-toggle input for a list of scannable codes (EAN, stock ID, ...).
   *
   * Two shapes, selected by whether `codes`/`onremove` are passed:
   *  - List mode (EAN codes, stock IDs on an entry): `codes` holds existing
   *    { id, code } rows rendered as removable chips; `onadd` is called when
   *    Enter/the Add button is used, and the parent clears `value` itself.
   *  - Single-value mode (a form's own stock-ID field): omit `codes`/`onadd`;
   *    `value` is bindable and the scan result is written straight into it.
   *
   * The scan-toggle button always shows the same scan icon, so scannable
   * fields look and behave the same everywhere in the app.
   *
   * Props:
   *   codes    — [{ id, code }] shown as removable chips (default: none)
   *   value    — bindable input value
   *   hint     — optional hint paragraph above the chips
   *   placeholder
   *   onadd()  — called on Enter / the Add button (list mode only)
   *   onremove(id) — called when a chip's remove button is clicked
   *   onscan(code) — called when the barcode scanner reads a code
   */
  let {
    codes = [],
    value = $bindable(''),
    hint = '',
    placeholder = '',
    onadd,
    onremove,
    onscan,
  } = $props();

  let scannerActive = $state(false);

  function handleScan(code) {
    scannerActive = false;
    onscan?.(code);
  }
</script>

{#if hint}
  <p class="text-sm text-gray-500">{hint}</p>
{/if}

{#if codes.length > 0}
  <div class="flex flex-wrap gap-2">
    {#each codes as c}
      <span class="inline-flex items-center gap-1.5 font-mono text-xs bg-gray-100 rounded-md px-2.5 py-1">
        {c.code}
        <button onclick={() => onremove?.(c.id)} class="text-gray-400 hover:text-red-600">
          <X size={12} />
        </button>
      </span>
    {/each}
  </div>
{/if}

{#if scannerActive}
  <BarcodeScanner active={true} onscan={handleScan} />
  <button type="button" onclick={() => scannerActive = false}
    class="w-full py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
    {t('common.stop_scan')}
  </button>
{:else}
  <div class="flex gap-2">
    <input bind:value {placeholder}
      onkeydown={(e) => e.key === 'Enter' && onadd?.()}
      class="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono" />
    {#if onadd}
      <button type="button" onclick={onadd} class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
        {t('common.add')}
      </button>
    {/if}
    <button type="button" onclick={() => scannerActive = true}
      aria-label={t('common.start_scan')} title={t('common.start_scan')}
      class="px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center gap-1.5">
      <ScanLine size={16} />
    </button>
  </div>
{/if}
