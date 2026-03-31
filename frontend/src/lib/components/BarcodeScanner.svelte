<script>
  import { onMount, onDestroy } from 'svelte';
  import { t } from '$lib/i18n.js';

  let { onscan, active = false } = $props();

  let containerId = 'qr-reader-' + Math.random().toString(36).slice(2);
  let scanner = null;
  let status = $state('idle'); // idle | starting | active | error
  let errorMsg = $state('');

  let _lastCode = '';
  let _lastCodeTime = 0;
  const SCAN_COOLDOWN_MS = 1500;

  function beep() {
    try {
      const ctx = new AudioContext();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = 'sine';
      osc.frequency.value = 640; // A4
      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.3);
      osc.onended = () => ctx.close();
    } catch {}
  }

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
          const now = Date.now();
          if (code === _lastCode && now - _lastCodeTime < SCAN_COOLDOWN_MS) return;
          _lastCode = code;
          _lastCodeTime = now;
          beep();
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
