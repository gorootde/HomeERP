<script>
  import { X } from 'lucide-svelte';

  let { title = '', wide = false, onclose, children } = $props();
</script>

<div class="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
  <div class="absolute inset-0 bg-black/50" onclick={onclose}></div>
  <div class={`relative bg-white rounded-t-2xl sm:rounded-xl shadow-xl w-full ${wide ? 'sm:max-w-2xl' : 'sm:max-w-lg'} max-h-[90dvh] flex flex-col`}>
    <div class="flex items-center justify-between px-5 py-4 border-b border-gray-200 shrink-0">
      <h2 class="text-base font-semibold text-gray-900">{title}</h2>
      <button onclick={onclose} class="p-1 rounded-lg hover:bg-gray-100 text-gray-500">
        <X size={20} />
      </button>
    </div>
    <div class="overflow-y-auto flex-1 p-5">
      {@render children()}
    </div>
  </div>
</div>
