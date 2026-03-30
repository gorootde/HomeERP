<script>
  import { onMount, onDestroy } from 'svelte';
  import { t } from '$lib/i18n.js';

  let { onscan, active = false } = $props();

  let containerId = 'qr-reader-' + Math.random().toString(36).slice(2);
  let scanner = null;
  let status = $state('idle'); // idle | starting | active | error
  let errorMsg = $state('');

  async function start() {
    if (typeof window === 'undefined') return;
    const { Html5Qrcode } = await import('html5-qrcode');
    status = 'starting';
    try {
      scanner = new Html5Qrcode(containerId);
      await scanner.start(
        { facingMode: 'environment' },
        { fps: 10, qrbox: { width: 250, height: 150 } },
        (code) => {
          onscan?.(code);
        },
        () => {}
      );
      status = 'active';
    } catch (e) {
      status = 'error';
      errorMsg = String(e);
    }
  }

  async function stop() {
    if (scanner) {
      try { await scanner.stop(); } catch {}
      scanner = null;
    }
    status = 'idle';
  }

  $effect(() => {
    if (active) {
      start();
    } else {
      stop();
    }
  });

  onDestroy(() => { stop(); });
</script>

<div class="space-y-2">
  <div id={containerId} class="w-full rounded-lg overflow-hidden bg-gray-100 min-h-[200px]"></div>
  {#if status === 'starting'}
    <p class="text-sm text-gray-500 text-center">{t('scanner.status_starting')}</p>
  {:else if status === 'active'}
    <p class="text-sm text-green-600 text-center">{t('scanner.status_active')}</p>
  {:else if status === 'error'}
    <p class="text-sm text-red-600 text-center">{errorMsg}</p>
  {/if}
</div>
