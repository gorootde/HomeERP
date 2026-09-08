<script>
  import { onMount } from 'svelte';
  import { t } from '$lib/i18n.svelte.js';
  import { showToast } from '$lib/toast.js';
  import {
    getProducts, getProduct, deleteProduct,
    addEan, removeEan, getUnits, getCategories
  } from '$lib/api.js';
  import Modal from '$lib/components/Modal.svelte';
  import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
  import ScannableCodeList from '$lib/components/ScannableCodeList.svelte';
  import DataTable from '$lib/components/DataTable.svelte';
  import ProductEditModal from '$lib/components/ProductEditModal.svelte';
  import { Plus, Pencil, Barcode, Trash2, Image } from 'lucide-svelte';

  let products = $state([]);
  let units = $state([]);
  let categories = $state([]);
  let loading = $state(true);

  // Modals
  let editModal = $state(null); // null | { productId: number | null }
  let eanModal = $state(null);  // null | { product }
  let confirmDelete = $state(null); // null | { id, name }

  // EAN modal state
  let eanList = $state([]);
  let eanInput = $state('');

  const searchProduct = (p, q) => {
    const s = q.toLowerCase();
    return !!p.name?.toLowerCase().includes(s) || !!p.vendor?.toLowerCase().includes(s);
  };

  onMount(async () => {
    await reload();
  });

  async function reload() {
    loading = true;
    try {
      [products, units, categories] = await Promise.all([
        getProducts('', 500), getUnits(), getCategories()
      ]);
    } finally {
      loading = false;
    }
  }

  function openAdd() {
    editModal = { productId: null };
  }

  function openEdit(id) {
    editModal = { productId: id };
  }

  async function confirmDeleteProduct() {
    try {
      await deleteProduct(confirmDelete.id);
      showToast(t('products.toast_deleted'), 'success');
      confirmDelete = null;
      await reload();
    } catch (e) {
      showToast(String(e), 'error');
    }
  }

  // EAN management
  async function openEanModal(productId) {
    const p = await getProduct(productId);
    eanList = [...(p.ean_codes || [])];
    eanInput = '';
    eanModal = { product: p };
  }

  async function addEanCode() {
    const code = eanInput.trim();
    if (!code) return;
    try {
      await addEan(eanModal.product.id, code);
      showToast(t('products.ean_toast_added'), 'success');
      const p = await getProduct(eanModal.product.id);
      eanList = [...(p.ean_codes || [])];
      eanInput = '';
    } catch (e) {
      showToast(String(e), 'error');
    }
  }

  async function removeEanCode(eanId) {
    await removeEan(eanModal.product.id, eanId);
    showToast(t('products.ean_toast_removed'), 'success');
    const p = await getProduct(eanModal.product.id);
    eanList = [...(p.ean_codes || [])];
  }

  function handleEanScan(code) {
    eanInput = code;
    addEanCode();
  }
</script>

<div class="px-4 md:px-6 py-5 max-w-5xl">
  <!-- Header -->
  <div class="flex flex-wrap items-center gap-3 mb-5">
    <h1 class="text-xl font-bold text-gray-900 flex-1">{t('products.title')}</h1>
    <button onclick={openAdd}
      class="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 shrink-0">
      <Plus size={16} /> {t('products.btn_add')}
    </button>
  </div>

  {#if loading}
    <div class="flex justify-center py-16 text-gray-400">{t('common.loading')}</div>
  {:else}
    {#snippet productCell(p)}
      <div class="flex items-center gap-3">
        {#if p.image_path}
          <img src={p.image_path} alt={p.name}
            class="w-9 h-9 rounded-lg object-cover shrink-0 bg-gray-100" />
        {:else}
          <div class="w-9 h-9 rounded-lg bg-gray-100 flex items-center justify-center shrink-0">
            <Image size={16} class="text-gray-400" />
          </div>
        {/if}
        <div class="min-w-0">
          <p class="font-medium text-gray-900 truncate">{p.name}</p>
          {#if p.vendor}<p class="text-xs text-gray-500 truncate">{p.vendor}</p>{/if}
        </div>
      </div>
    {/snippet}
    {#snippet unitCell(p)}
      <span class="text-gray-500">{p.unit ? `${p.unit.name} (${p.unit.abbreviation})` : '—'}</span>
    {/snippet}
    {#snippet eansCell(p)}
      <div class="flex flex-wrap gap-1">
        {#each p.ean_codes || [] as ean}
          <span class="text-xs font-mono bg-gray-100 text-gray-600 rounded px-1.5 py-0.5">{ean.code}</span>
        {/each}
      </div>
    {/snippet}
    {#snippet tagsCell(p)}
      <div class="flex flex-wrap gap-1">
        {#each p.tags || [] as tag}
          <span class="text-xs bg-indigo-100 text-indigo-700 rounded-full px-2 py-0.5">{tag.name}</span>
        {/each}
      </div>
    {/snippet}
    {#snippet actionsCell(p)}
      <div class="flex items-center gap-1 justify-end">
        <button onclick={() => openEanModal(p.id)} title={t('products.btn_eans')}
          class="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100">
          <Barcode size={16} />
        </button>
        <button onclick={() => openEdit(p.id)} title={t('products.btn_edit')}
          class="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100">
          <Pencil size={16} />
        </button>
        <button onclick={() => confirmDelete = { id: p.id, name: p.name }}
          class="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50">
          <Trash2 size={16} />
        </button>
      </div>
    {/snippet}
    <DataTable
      card
      rows={products}
      rowKey={(p) => p.id}
      search={searchProduct}
      searchPlaceholder={t('products.search_placeholder')}
      actions={actionsCell}
      columns={[
          { key: 'product', label: t('products.col_product'), sortable: true,
            value: (p) => p.name, cell: productCell },
          { key: 'unit', label: t('products.col_unit'), hideBelow: 'sm', sortable: true,
            value: (p) => p.unit?.name, cell: unitCell },
          { key: 'eans', label: t('products.col_eans'), hideBelow: 'md', cell: eansCell },
          { key: 'tags', label: t('products.col_tags'), hideBelow: 'lg', cell: tagsCell },
          { key: 'category', hidden: true, label: t('products.label_category'),
            filter: {
              kind: 'select',
              placeholder: t('products.filter_all_categories'),
              options: [
                ...categories.map((c) => ({ value: String(c.id), label: c.name })),
                { value: 'none', label: t('common.no_category') },
              ],
              match: (p, v) => v === 'none' ? p.category_id == null : p.category_id === Number(v),
            } },
      ]}>
      {#snippet empty()}
        <p class="text-center text-gray-400 py-12">{t('products.empty')}</p>
      {/snippet}
    </DataTable>
  {/if}
</div>

<!-- Edit/Add Modal -->
{#if editModal}
  <ProductEditModal
    productId={editModal.productId}
    {units}
    {categories}
    onsaved={() => { editModal = null; reload(); }}
    onclose={() => editModal = null} />
{/if}

<!-- EAN Modal -->
{#if eanModal}
  <Modal title={t('products.ean_modal_title')} onclose={() => { eanModal = null; }}>
    <div class="space-y-4">
      <ScannableCodeList
        codes={eanList}
        bind:value={eanInput}
        hint={t('products.ean_modal_hint')}
        placeholder={t('products.ean_placeholder')}
        onadd={addEanCode}
        onremove={removeEanCode}
        onscan={handleEanScan} />
      <div class="flex justify-end pt-1">
        <button onclick={() => { eanModal = null; reload(); }}
          class="px-4 py-2 text-sm bg-gray-800 text-white rounded-lg hover:bg-gray-700">
          {t('products.ean_btn_done')}
        </button>
      </div>
    </div>
  </Modal>
{/if}

<!-- Confirm Delete -->
{#if confirmDelete}
  <ConfirmDialog
    message={t('products.confirm_delete')}
    onconfirm={confirmDeleteProduct}
    oncancel={() => confirmDelete = null} />
{/if}
