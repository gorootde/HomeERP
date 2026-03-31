<script>
  import { t } from '$lib/i18n.js';

  let { message, onconfirm, oncancel } = $props();
</script>

<div class="fixed inset-0 z-50 flex items-center justify-center">
  <div class="absolute inset-0 bg-black/50" onclick={oncancel}></div>
  <div class="relative bg-white rounded-xl shadow-xl w-full max-w-sm mx-4 p-6">
    <p class="text-sm text-gray-700 mb-5">{message}</p>
    <div class="flex gap-3 justify-end">
      <button onclick={oncancel}
        class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">
        {t('common.cancel')}
      </button>
      <button onclick={onconfirm}
        class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700">
        {t('common.delete')}
      </button>
    </div>
  </div>
</div>
