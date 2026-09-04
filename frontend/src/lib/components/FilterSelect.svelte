<script>
  /**
   * Styled <select> for filter bars (stock, history).
   * Props:
   *   value       — bindable selected value
   *   options     — [{ value, label }]
   *   placeholder — label for the unset/"all" option (value = ''); omit to
   *                 not render one
   *   onchange    — optional; pages that filter server-side pass a reload callback
   */
  let { value = $bindable(''), options = [], placeholder = '', onchange } = $props();
</script>

<select bind:value {onchange}
  class="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
  {#if placeholder}<option value="">{placeholder}</option>{/if}
  {#each options as opt}
    <option value={opt.value}>{opt.label}</option>
  {/each}
</select>
