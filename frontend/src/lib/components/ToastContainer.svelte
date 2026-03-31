<script>
  import { toasts, dismissToast } from '$lib/toast.js';
  import { CheckCircle, AlertCircle, Info, X } from 'lucide-svelte';
</script>

<div class="fixed top-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
  {#each $toasts as toast (toast.id)}
    <div class="pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg text-sm font-medium max-w-sm
      {toast.type === 'success' ? 'bg-green-600 text-white' :
       toast.type === 'error' ? 'bg-red-600 text-white' :
       'bg-gray-900 text-white'}">
      {#if toast.type === 'success'}
        <CheckCircle size={16} class="shrink-0" />
      {:else if toast.type === 'error'}
        <AlertCircle size={16} class="shrink-0" />
      {:else}
        <Info size={16} class="shrink-0" />
      {/if}
      <span class="flex-1">{toast.message}</span>
      <button onclick={() => dismissToast(toast.id)} class="shrink-0 opacity-70 hover:opacity-100">
        <X size={14} />
      </button>
    </div>
  {/each}
</div>
