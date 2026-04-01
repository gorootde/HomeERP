<script>
  import { onDestroy } from 'svelte';
  import { t } from '$lib/i18n.js';

  let { onscan, active = false } = $props();

  let containerId = 'qr-reader-' + Math.random().toString(36).slice(2);
  let scanner = null;
  let status = $state('idle'); // idle | starting | active | error
  let errorMsg = $state('');
  let zoomMin = $state(1);
  let zoomMax = $state(1);
  let zoomValue = $state(1);
  let hasZoom = $state(false);
  let resolution = $state('');

  let _lastCode = '';
  let _lastCodeTime = 0;
  const SCAN_COOLDOWN_MS = 1500;

  // jsQR loop state
  let jsqrCanvas = null;
  let jsqrCtx = null;
  let jsqrRafId = null;
  let jsqrLib = null;

  function beep() {
    try {
      const ctx = new AudioContext();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = 'sine';
      osc.frequency.value = 640;
      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.3);
      osc.onended = () => ctx.close();
    } catch {}
  }

  function handleCode(code) {
    const now = Date.now();
    if (code === _lastCode && now - _lastCodeTime < SCAN_COOLDOWN_MS) return;
    _lastCode = code;
    _lastCodeTime = now;
    beep();
    onscan?.(code);
  }

  function startJsQrLoop(videoEl) {
    if (!jsqrLib || !videoEl) return;
    jsqrCanvas = document.createElement('canvas');
    jsqrCtx = jsqrCanvas.getContext('2d', { willReadFrequently: true });

    function tick() {
      if (!videoEl || videoEl.readyState < 2) { jsqrRafId = requestAnimationFrame(tick); return; }
      const w = videoEl.videoWidth;
      const h = videoEl.videoHeight;
      if (w && h) {
        jsqrCanvas.width = w;
        jsqrCanvas.height = h;
        jsqrCtx.drawImage(videoEl, 0, 0, w, h);
        try {
          const result = jsqrLib.decodeFromCanvas(jsqrCanvas);
          if (result) handleCode(result.getText());
        } catch {}
      }
      jsqrRafId = requestAnimationFrame(tick);
    }
    jsqrRafId = requestAnimationFrame(tick);
  }

  function stopJsQrLoop() {
    if (jsqrRafId) { cancelAnimationFrame(jsqrRafId); jsqrRafId = null; }
    jsqrCanvas = null;
    jsqrCtx = null;
  }

  async function applyZoom(value) {
    zoomValue = value;
    try { await scanner?.applyVideoConstraints({ advanced: [{ zoom: value }] }); } catch {}
  }

  async function start() {
    if (typeof window === 'undefined') return;
    const [{ Html5Qrcode }, { BrowserMultiFormatReader }] = await Promise.all([
      import('html5-qrcode'),
      import('@zxing/browser')
    ]);
    jsqrLib = new BrowserMultiFormatReader();
    status = 'starting';
    try {
      scanner = new Html5Qrcode(containerId);
      await scanner.start(
        { facingMode: 'environment' },
        {
          fps: 10,
          qrbox: (w, h) => ({ width: Math.round(w * 0.95), height: Math.round(h * 0.95) }),
          videoConstraints: { facingMode: { ideal: 'environment' }, width: { ideal: 3840 }, height: { ideal: 2160 } },
        },
        (code) => handleCode(code),
        () => {}
      );

      // Show actual resolution
      try {
        const settings = scanner.getRunningTrackSettings?.();
        if (settings?.width && settings?.height) resolution = `${settings.width}×${settings.height}`;
      } catch {}

      // Detect zoom
      try {
        const caps = scanner.getRunningTrackCapabilities?.();
        if (caps?.zoom) {
          zoomMin = caps.zoom.min ?? 1;
          zoomMax = caps.zoom.max ?? 1;
          zoomValue = Math.min(4, zoomMax);
          hasZoom = zoomMax > zoomMin;
          if (hasZoom) await scanner.applyVideoConstraints({ advanced: [{ zoom: zoomValue }] });
        }
      } catch {}

      // Start jsQR loop on the native video element for full-resolution QR detection
      const videoEl = document.querySelector(`#${containerId} video`);
      startJsQrLoop(videoEl);

      status = 'active';
    } catch (e) {
      status = 'error';
      errorMsg = String(e);
    }
  }

  async function stop() {
    stopJsQrLoop();
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
    <p class="text-sm text-green-600 text-center">{t('scanner.status_active')}{resolution ? ` · ${resolution}` : ''}</p>
    {#if hasZoom}
      <div class="flex items-center gap-2 px-1">
        <span class="text-xs text-gray-500 shrink-0">🔍 {zoomValue.toFixed(1)}×</span>
        <input type="range" min={zoomMin} max={zoomMax} step="0.1"
          value={zoomValue}
          oninput={(e) => applyZoom(Number(e.target.value))}
          class="flex-1 accent-blue-600" />
      </div>
    {/if}
  {:else if status === 'error'}
    <p class="text-sm text-red-600 text-center">{errorMsg}</p>
  {/if}
</div>
