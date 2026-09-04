<script>
  import { t } from '$lib/i18n.svelte.js';

  let { message, onconfirm, oncancel, confirmLabel = null } = $props();
</script>

<div class="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
  <div class="absolute inset-0 bg-black/50" onclick={oncancel}></div>
  <div role="alertdialog" aria-modal="true"
    class="relative bg-white rounded-t-2xl sm:rounded-xl shadow-xl w-full sm:max-w-sm p-6">
    <p class="text-sm text-gray-700 mb-5">{message}</p>
    <div class="flex gap-3 justify-end">
      <button onclick={oncancel}
        class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">
        {t('common.cancel')}
      </button>
      <button onclick={onconfirm}
        class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700">
        {confirmLabel ?? t('common.delete')}
      </button>
    </div>
  </div>
</div>
