<script>
  import { X, Plus } from 'lucide-svelte';
  import { t } from '$lib/i18n.js';

  let { tags = [], onadd, onremove, readonly = false } = $props();
  let input = $state('');

  function add() {
    const name = input.trim();
    if (!name) return;
    onadd?.(name);
    input = '';
  }

  function keydown(e) {
    if (e.key === 'Enter') { e.preventDefault(); add(); }
  }
</script>

<div class="flex flex-wrap gap-1.5">
  {#each tags as tag}
    <span class="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
      {tag.name}
      {#if !readonly}
        <button onclick={() => onremove?.(tag.name)} class="hover:text-blue-900">
          <X size={12} />
        </button>
      {/if}
    </span>
  {/each}
  {#if !readonly}
    <div class="flex items-center gap-1">
      <input bind:value={input} onkeydown={keydown}
        placeholder={t('common.tag_input_placeholder')}
        class="text-xs border border-gray-300 rounded-full px-2 py-0.5 w-28 focus:outline-none focus:ring-1 focus:ring-blue-500" />
      <button onclick={add} class="text-blue-600 hover:text-blue-800">
        <Plus size={14} />
      </button>
    </div>
  {/if}
</div>
