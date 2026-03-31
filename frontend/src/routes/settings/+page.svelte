<script>
  import { t, locale, setLocale } from '$lib/i18n.js';
  import { Tag, Layers, Ruler, LayoutList, ArrowLeftRight, Languages } from 'lucide-svelte';

  const cards = [
    { href: '/settings/stockid', icon: Tag, titleKey: 'settings.stockid_title', descKey: 'settings.stockid_desc' },
    { href: '/settings/vaults', icon: Layers, titleKey: 'settings.vaults_title', descKey: 'settings.vaults_desc' },
    { href: '/settings/units', icon: Ruler, titleKey: 'settings.units_title', descKey: 'settings.units_desc' },
    { href: '/settings/categories', icon: LayoutList, titleKey: 'settings.categories_title', descKey: 'settings.categories_desc' },
    { href: '/settings/data-transfer', icon: ArrowLeftRight, titleKey: 'settings.data_transfer_title', descKey: 'settings.data_transfer_desc' },
  ];
</script>

<div class="px-4 md:px-6 py-5 max-w-2xl">
  <h1 class="text-xl font-bold text-gray-900 mb-5">{t('settings.title')}</h1>

  <div class="space-y-2 mb-6">
    {#each cards as card}
      <a href={card.href}
        class="flex items-center gap-4 bg-white rounded-xl border border-gray-200 px-4 py-3.5 hover:bg-gray-50 transition-colors">
        <svelte:component this={card.icon} size={20} class="text-gray-500 shrink-0" />
        <div class="min-w-0">
          <p class="text-sm font-medium text-gray-900">{t(card.titleKey)}</p>
          <p class="text-xs text-gray-500 truncate">{t(card.descKey)}</p>
        </div>
        <svg class="ml-auto text-gray-400 shrink-0" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
      </a>
    {/each}
  </div>

  <!-- Language -->
  <div class="bg-white rounded-xl border border-gray-200 px-4 py-4">
    <div class="flex items-center gap-3 mb-3">
      <Languages size={20} class="text-gray-500" />
      <div>
        <p class="text-sm font-medium text-gray-900">{t('settings.language_title')}</p>
        <p class="text-xs text-gray-500">{t('settings.language_desc')}</p>
      </div>
    </div>
    <div class="flex gap-2">
      <button onclick={() => setLocale('de')}
        class="flex-1 py-2 text-sm font-medium rounded-lg border transition-colors
          {$locale === 'de' ? 'bg-blue-600 text-white border-transparent' : 'border-gray-300 hover:bg-gray-50'}">
        {t('settings.lang_de')}
      </button>
      <button onclick={() => setLocale('en')}
        class="flex-1 py-2 text-sm font-medium rounded-lg border transition-colors
          {$locale === 'en' ? 'bg-blue-600 text-white border-transparent' : 'border-gray-300 hover:bg-gray-50'}">
        {t('settings.lang_en')}
      </button>
    </div>
  </div>
</div>
