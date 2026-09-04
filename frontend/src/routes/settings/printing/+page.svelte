<script>
  import { onMount } from 'svelte';
  import { t } from '$lib/i18n.svelte.js';
  import { showToast } from '$lib/toast.js';
  import { getSettings, saveSettings, getLabelOptions, getLabelPreviewUrl, testPrintLabel, clearPrintQueue } from '$lib/api.js';
  import { ChevronLeft } from 'lucide-svelte';

  let loading = $state(true);
  let printerIp = $state('');
  let protocol = $state('ipp');
  let model = $state('QL-710W');
  let autoPrint = $state(false);
  let widthMm = $state('62');
  let lengthMm = $state('90');
  let lengthMode = $state('auto');
  let orientation = $state('landscape');
  let widthChoices = $state([12, 19, 29, 38, 50, 54, 62, 102]);
  let orientationChoices = $state(['landscape', 'portrait']);
  let lengthModeChoices = $state(['auto', 'fixed']);
  let protocolChoices = $state(['ipp', 'brother_ql']);
  let testing = $state(false);
  let clearing = $state(false);

  let previewUrl = $derived(getLabelPreviewUrl(widthMm, lengthMm, orientation, lengthMode));

  onMount(async () => {
    const [settings, options] = await Promise.all([getSettings(), getLabelOptions().catch(() => null)]);
    const s = (key) => settings.find(x => x.key === key)?.value || '';
    printerIp = s('label_printer_ip');
    protocol = s('label_printer_protocol') || 'ipp';
    model = s('label_printer_model') || 'QL-710W';
    autoPrint = s('label_auto_print') === '1';
    widthMm = s('label_width_mm') || '62';
    lengthMm = s('label_length_mm') || '90';
    lengthMode = s('label_length_mode') || 'auto';
    orientation = s('label_orientation') || 'landscape';
    if (options?.width_choices_mm) widthChoices = options.width_choices_mm;
    if (options?.orientation_choices) orientationChoices = options.orientation_choices;
    if (options?.length_mode_choices) lengthModeChoices = options.length_mode_choices;
    if (options?.protocol_choices) protocolChoices = options.protocol_choices;
    loading = false;
  });

  async function persist() {
    await saveSettings({
      label_printer_ip: printerIp,
      label_printer_protocol: protocol,
      label_printer_model: model,
      label_auto_print: autoPrint ? '1' : '0',
      label_width_mm: String(widthMm),
      label_length_mm: String(lengthMm),
      label_length_mode: lengthMode,
      label_orientation: orientation,
    });
  }

  async function clearQueue() {
    clearing = true;
    try {
      await persist();
      await clearPrintQueue();
      showToast(t('printing.toast_queue_cleared'), 'success');
    } catch (e) {
      showToast(`${t('printing.toast_queue_error')}: ${e}`, 'error');
    } finally {
      clearing = false;
    }
  }

  async function save() {
    try {
      await persist();
      showToast(t('printing.toast_saved'), 'success');
    } catch (e) { showToast(String(e), 'error'); }
  }

  async function testPrint() {
    testing = true;
    try {
      await persist();                 // test-print uses the stored settings
      await testPrintLabel();
      showToast(t('printing.toast_test_success'), 'success');
    } catch (e) {
      showToast(`${t('printing.toast_test_error')}: ${e}`, 'error');
    } finally {
      testing = false;
    }
  }
</script>

<div class="px-4 md:px-6 py-5 max-w-lg">
  <div class="flex items-center gap-3 mb-5">
    <a href="/settings" class="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500"><ChevronLeft size={20} /></a>
    <h1 class="text-xl font-bold text-gray-900">{t('printing.title')}</h1>
  </div>

  {#if loading}
    <div class="flex justify-center py-16 text-gray-400">{t('common.loading')}</div>
  {:else}
    <div class="space-y-4">
      <!-- Label preview -->
      <div>
        <p class="text-xs font-medium text-gray-700 mb-1">{t('printing.label_preview')}</p>
        <div class="bg-white rounded-xl border border-gray-200 p-3 flex justify-center">
          <img src={previewUrl} alt={t('printing.label_preview')}
            class="w-full max-w-sm rounded border border-gray-100" />
        </div>
      </div>

      <!-- Label dimensions -->
      <div class="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1" for="label-orientation">
            {t('printing.label_orientation')}
          </label>
          <select id="label-orientation" bind:value={orientation}
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
            {#each orientationChoices as o}
              <option value={o}>{t(`printing.orientation_${o}`)}</option>
            {/each}
          </select>
          <p class="text-xs text-gray-400 mt-0.5">{t('printing.hint_orientation')}</p>
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1" for="label-width">
            {t('printing.label_width')}
          </label>
          <select id="label-width" bind:value={widthMm}
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
            {#each widthChoices as w}
              <option value={String(w)}>{w} mm</option>
            {/each}
          </select>
          <p class="text-xs text-gray-400 mt-0.5">{t('printing.hint_width')}</p>
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1" for="label-length-mode">
            {t('printing.label_length')}
          </label>
          <select id="label-length-mode" bind:value={lengthMode}
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
            {#each lengthModeChoices as m}
              <option value={m}>{t(`printing.length_mode_${m}`)}</option>
            {/each}
          </select>
          {#if lengthMode === 'fixed'}
            <div class="flex items-center gap-2 mt-2">
              <input id="label-length" bind:value={lengthMm} type="number" min="15" max="500" step="1"
                class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
              <span class="text-sm text-gray-500 shrink-0">mm</span>
            </div>
          {/if}
          <p class="text-xs text-gray-400 mt-0.5">
            {lengthMode === 'fixed' ? t('printing.hint_length_fixed') : t('printing.hint_length_auto')}
          </p>
        </div>
      </div>

      <!-- Printer -->
      <div class="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1" for="printer-ip">
            {t('printing.label_printer_ip')}
          </label>
          <input id="printer-ip" bind:value={printerIp} placeholder={t('printing.placeholder_printer_ip')}
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono" />
          <p class="text-xs text-gray-400 mt-0.5">{t('printing.hint_printer_ip')}</p>
        </div>

        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1" for="printer-protocol">
            {t('printing.label_protocol')}
          </label>
          <select id="printer-protocol" bind:value={protocol}
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
            {#each protocolChoices as p}
              <option value={p}>{t(`printing.protocol_${p}`)}</option>
            {/each}
          </select>
          <p class="text-xs text-gray-400 mt-0.5">{t('printing.hint_protocol')}</p>
        </div>

        {#if protocol === 'brother_ql'}
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1" for="printer-model">
              {t('printing.label_model')}
            </label>
            <input id="printer-model" bind:value={model} placeholder="QL-710W"
              class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono" />
            <p class="text-xs text-gray-400 mt-0.5">{t('printing.hint_model')}</p>
          </div>
        {/if}

        <button onclick={testPrint} disabled={!printerIp || testing}
          class="w-full py-2 text-sm font-medium border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50">
          {t('printing.btn_test_print')}
        </button>
        {#if protocol === 'ipp'}
          <button onclick={clearQueue} disabled={!printerIp || clearing}
            class="w-full py-2 text-sm font-medium border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50">
            {t('printing.btn_clear_queue')}
          </button>
        {/if}
      </div>

      <!-- Auto print -->
      <label class="flex items-start gap-3 bg-white rounded-xl border border-gray-200 p-4 cursor-pointer">
        <input type="checkbox" bind:checked={autoPrint} class="mt-0.5" />
        <div>
          <p class="text-sm font-medium text-gray-900">{t('printing.label_auto_print')}</p>
          <p class="text-xs text-gray-500">{t('printing.hint_auto_print')}</p>
        </div>
      </label>

      <button onclick={save}
        class="w-full py-2.5 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700">
        {t('printing.btn_save')}
      </button>
    </div>
  {/if}
</div>
