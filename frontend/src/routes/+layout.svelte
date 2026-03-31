<script>
  import '../app.css';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { t, locale } from '$lib/i18n.js';
  import ToastContainer from '$lib/components/ToastContainer.svelte';
  import { getOpenApiSpec } from '$lib/api.js';
  import { onMount } from 'svelte';
  import {
    LayoutDashboard, Boxes, Layers, ScanBarcode, ClipboardCheck,
    Settings, Code2, MoreHorizontal, Package2
  } from 'lucide-svelte';

  let { children } = $props();
  let version = $state('');
  let moreMenuOpen = $state(false);

  const navItems = [
    { href: '/dashboard', icon: LayoutDashboard, labelKey: 'nav.dashboard' },
    { href: '/products', icon: Boxes, labelKey: 'nav.products' },
    { href: '/stock', icon: Layers, labelKey: 'nav.stock' },
    { href: '/scanner', icon: ScanBarcode, labelKey: 'nav.scanner' },
    { href: '/inventory', icon: ClipboardCheck, labelKey: 'nav.inventory' },
  ];

  const bottomPrimary = [
    { href: '/dashboard', icon: LayoutDashboard, labelKey: 'nav.home' },
    { href: '/products', icon: Boxes, labelKey: 'nav.products' },
    { href: '/stock', icon: Layers, labelKey: 'nav.stock' },
    { href: '/scanner', icon: ScanBarcode, labelKey: 'nav.scan' },
  ];

  const moreItems = [
    { href: '/inventory', icon: ClipboardCheck, labelKey: 'nav.inventory' },
    { href: '/settings', icon: Settings, labelKey: 'nav.settings' },
    { href: '/apidocs', icon: Code2, labelKey: 'nav.apidocs' },
  ];

  onMount(async () => {
    try {
      const spec = await getOpenApiSpec();
      version = spec?.info?.version || '';
    } catch {}
  });

  function isActive(href) {
    return $page.url.pathname.startsWith(href);
  }

  function closeMore() { moreMenuOpen = false; }

  function navigateMore(href) {
    moreMenuOpen = false;
    goto(href);
  }
</script>

<div class="flex min-h-dvh bg-gray-50">
  <!-- Desktop sidebar -->
  <nav class="hidden md:flex flex-col fixed inset-y-0 left-0 w-60 bg-white border-r border-gray-200 z-30">
    <div class="flex items-center gap-2.5 px-5 h-14 border-b border-gray-200 shrink-0">
      <Package2 size={22} class="text-blue-600" />
      <span class="font-semibold text-gray-900 text-sm">HomeERP</span>
    </div>
    <ul class="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
      {#each navItems as item}
        <li>
          <a href={item.href}
            class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors
              {isActive(item.href)
                ? 'bg-blue-50 text-blue-700'
                : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'}">
            <svelte:component this={item.icon} size={18} />
            {t(item.labelKey)}
          </a>
        </li>
      {/each}
    </ul>
    <div class="border-t border-gray-200 py-3 px-2 space-y-0.5">
      <a href="/settings"
        class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors
          {isActive('/settings') ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'}">
        <Settings size={18} />
        {t('nav.settings')}
      </a>
      <a href="/apidocs"
        class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors
          {isActive('/apidocs') ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'}">
        <Code2 size={18} />
        {t('nav.apidocs')}
      </a>
      {#if version}
        <p class="px-3 text-xs text-gray-400 pt-1">v{version}</p>
      {/if}
    </div>
  </nav>

  <!-- Main content -->
  <main class="flex-1 md:ml-60 pb-20 md:pb-0 min-w-0">
    {@render children()}
  </main>

  <!-- Mobile bottom nav -->
  <nav class="md:hidden fixed bottom-0 inset-x-0 bg-white border-t border-gray-200 z-30
    flex items-stretch h-16 safe-area-bottom">
    {#each bottomPrimary as item}
      <a href={item.href}
        class="flex-1 flex flex-col items-center justify-center gap-0.5 text-xs font-medium transition-colors
          {isActive(item.href) ? 'text-blue-600' : 'text-gray-500'}">
        <svelte:component this={item.icon} size={20} />
        {t(item.labelKey)}
      </a>
    {/each}
    <button onclick={() => moreMenuOpen = true}
      class="flex-1 flex flex-col items-center justify-center gap-0.5 text-xs font-medium text-gray-500">
      <MoreHorizontal size={20} />
      {t('nav.more')}
    </button>
  </nav>

  <!-- More menu -->
  {#if moreMenuOpen}
    <div class="md:hidden fixed inset-0 z-40" onclick={closeMore}>
      <div class="absolute inset-0 bg-black/40"></div>
    </div>
    <div class="md:hidden fixed bottom-0 inset-x-0 z-50 bg-white rounded-t-2xl shadow-xl pb-safe">
      <div class="w-10 h-1 bg-gray-300 rounded-full mx-auto mt-3 mb-4"></div>
      <nav class="grid grid-cols-3 gap-2 px-4 pb-6">
        {#each moreItems as item}
          <button onclick={() => navigateMore(item.href)}
            class="flex flex-col items-center gap-1.5 px-2 py-3 rounded-xl text-xs font-medium
              {isActive(item.href) ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-100'}">
            <svelte:component this={item.icon} size={22} />
            {t(item.labelKey)}
          </button>
        {/each}
      </nav>
    </div>
  {/if}
</div>

<ToastContainer />

<style>
  .safe-area-bottom {
    padding-bottom: env(safe-area-inset-bottom, 0px);
    height: calc(4rem + env(safe-area-inset-bottom, 0px));
  }
  .pb-safe {
    padding-bottom: env(safe-area-inset-bottom, 0px);
  }
</style>
