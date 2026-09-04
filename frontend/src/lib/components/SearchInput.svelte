<script>
  import { Search } from 'lucide-svelte';

  /** Text search box with a leading search icon. Props: value (bindable), placeholder. */
  let { value = $bindable(''), placeholder = '' } = $props();
</script>

<div class="relative">
  <Search size={16} class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
  <input bind:value {placeholder}
    class="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
</div>
