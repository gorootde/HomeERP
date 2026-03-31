<script>
  import { t } from '$lib/i18n.js';
</script>

<div class="flex flex-col h-[calc(100dvh-4rem)] md:h-dvh">
  <div class="px-4 md:px-6 py-4 border-b border-gray-200 bg-white">
    <h1 class="text-lg font-bold text-gray-900">{t('nav.apidocs')}</h1>
  </div>
  <iframe src="/docs" title="API Documentation" class="flex-1 w-full border-0"></iframe>
</div>
