<script>
  import { onMount } from 'svelte';
  import { t } from '$lib/i18n.js';
  import { showToast } from '$lib/toast.js';
  import { getSettings, putSetting } from '$lib/api.js';
  import { ChevronLeft } from 'lucide-svelte';

  let loading = $state(true);
  let mode = $state('manual');
  let prefix = $state('');
  let counter = $state('1');
  let padLength = $state('4');
  let webhookUrl = $state('');

  onMount(async () => {
    const settings = await getSettings();
    const s = (key) => settings.find(x => x.key === key)?.value || '';
    mode = s('stock_id_mode') || 'manual';
    prefix = s('stock_id_prefix');
    counter = s('stock_id_counter') || '1';
    padLength = s('stock_id_pad_length') || '4';
    webhookUrl = s('stock_id_webhook_url');
    loading = false;
  });

  async function save() {
    try {
      await Promise.all([
        putSetting('stock_id_mode', mode),
        putSetting('stock_id_prefix', prefix),
        putSetting('stock_id_counter', counter),
        putSetting('stock_id_pad_length', padLength),
        putSetting('stock_id_webhook_url', webhookUrl)
      ]);
      showToast(t('stockid.toast_saved'), 'success');
    } catch (e) { showToast(String(e), 'error'); }
  }

  let nextId = $derived(() => {
    const n = parseInt(counter) || 1;
    const pad = parseInt(padLength) || 4;
    return prefix + String(n).padStart(pad, '0');
  });
</script>

<div class="px-4 md:px-6 py-5 max-w-lg">
  <div class="flex items-center gap-3 mb-5">
    <a href="/settings" class="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500"><ChevronLeft size={20} /></a>
    <h1 class="text-xl font-bold text-gray-900">{t('stockid.title')}</h1>
  </div>

  {#if loading}
    <div class="flex justify-center py-16 text-gray-400">Loading…</div>
  {:else}
    <div class="space-y-4">
      <!-- Mode selection -->
      <div class="space-y-2">
        {#each [['manual', 'stockid.mode_manual_title', 'stockid.mode_manual_desc'],
                ['generated', 'stockid.mode_auto_title', 'stockid.mode_auto_desc'],
                ['extern', 'stockid.mode_extern_title', 'stockid.mode_extern_desc']] as [val, titleKey, descKey]}
          <label class="flex items-start gap-3 bg-white rounded-xl border p-4 cursor-pointer
            {mode === val ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:bg-gray-50'}">
            <input type="radio" bind:group={mode} value={val} class="mt-0.5" />
            <div>
              <p class="text-sm font-medium text-gray-900">{t(titleKey)}</p>
              <p class="text-xs text-gray-500">{t(descKey)}</p>
            </div>
          </label>
        {/each}
      </div>

      <!-- Generated options -->
      {#if mode === 'generated'}
        <div class="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">{t('stockid.label_prefix')}</label>
            <input bind:value={prefix} placeholder={t('stockid.placeholder_prefix')}
              class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            <p class="text-xs text-gray-400 mt-0.5">{t('stockid.hint_prefix')}</p>
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">{t('stockid.label_counter')}</label>
            <input bind:value={counter} type="number" min="1"
              class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            <p class="text-xs text-blue-600 mt-0.5">{t('stockid.hint_next_id', { id: nextId() })}</p>
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">{t('stockid.label_pad')}</label>
            <input bind:value={padLength} type="number" min="1" max="20"
              class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            <p class="text-xs text-gray-400 mt-0.5">{t('stockid.hint_pad')}</p>
          </div>
        </div>
      {/if}

      <!-- Webhook options -->
      {#if mode === 'extern'}
        <div class="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">{t('stockid.label_webhook')}</label>
            <input bind:value={webhookUrl} placeholder="https://…"
              class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            <p class="text-xs text-gray-400 mt-0.5">{t('stockid.hint_webhook')}</p>
          </div>
          <!-- Placeholders -->
          <div>
            <p class="text-xs font-medium text-gray-700 mb-1">{t('stockid.placeholders_title')}</p>
            <div class="space-y-0.5">
              {#each ['ph_quantity','ph_product_id','ph_vault_id','ph_bbd','ph_comment'] as key}
                <p class="text-xs font-mono text-gray-500">{t(`stockid.${key}`)}</p>
              {/each}
            </div>
          </div>
        </div>
      {/if}

      <button onclick={save}
        class="w-full py-2.5 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700">
        {t('stockid.btn_save')}
      </button>
    </div>
  {/if}
</div>
