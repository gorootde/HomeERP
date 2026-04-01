<script>
  import { onMount } from 'svelte';
  import { t } from '$lib/i18n.js';
  import { showToast } from '$lib/toast.js';
  import {
    getProducts, getProduct, createProduct, updateProduct, deleteProduct,
    addEan, removeEan, getEanInfo, setImageFromUrl, uploadProductImage, deleteProductImage,
    getUnits, getCategories, getTags, addTagToProduct, removeTagFromProduct,
    getProductUnitConversions, addProductUnitConversion, deleteProductUnitConversion
  } from '$lib/api.js';
  import Modal from '$lib/components/Modal.svelte';
  import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
  import TagChips from '$lib/components/TagChips.svelte';
  import BarcodeScanner from '$lib/components/BarcodeScanner.svelte';
  import UnitConversionEditor from '$lib/components/UnitConversionEditor.svelte';
  import { Plus, Pencil, Barcode, Trash2, Image, X, Search } from 'lucide-svelte';

  let products = $state([]);
  let units = $state([]);
  let categories = $state([]);
  let allTags = $state([]);
  let loading = $state(true);
  let search = $state('');

  // Modals
  let editModal = $state(null); // null | { product, isNew }
  let eanModal = $state(null);  // null | { product }
  let confirmDelete = $state(null); // null | { id, name }

  // Edit form state
  let form = $state({ name: '', vendor: '', size: '', unit_id: '', entry_unit_key: '', category_id: '', tags: [], puc: [] });
  let formPhotoFile = $state(null);
  let formPhotoPreview = $state('');
  let offBanner = $state(null);

  // EAN modal state
  let eanList = $state([]);
  let eanInput = $state('');
  let eanScannerActive = $state(false);

  // Available entry units for the currently edited product (base + product conversions + global units with conversion)
  let entryUnitOptions = $derived(() => {
    const unitId = Number(form.unit_id);
    if (!unitId) return [];
    const result = [{ id: 'base', label: (() => { const u = units.find(u => u.id === unitId); return u ? `${u.name} (${u.abbreviation})` : 'Basiseinheit'; })() }];
    for (const puc of form.puc) {
      result.push({ id: 'puc_' + puc.id, label: puc.name });
    }
    for (const u of units) {
      if (u.id === unitId) continue;
      const conv = (u.conversions || []).find(c => c.to_unit?.id === unitId);
      if (conv) result.push({ id: 'global_' + u.id, label: `${u.name} (${u.abbreviation})` });
    }
    return result;
  });

  let filtered = $derived(
    products.filter(p =>
      !search ||
      p.name?.toLowerCase().includes(search.toLowerCase()) ||
      p.vendor?.toLowerCase().includes(search.toLowerCase())
    )
  );

  onMount(async () => {
    await reload();
  });

  async function reload() {
    loading = true;
    try {
      [products, units, categories, allTags] = await Promise.all([
        getProducts('', 500), getUnits(), getCategories(), getTags()
      ]);
    } finally {
      loading = false;
    }
  }

  function openAdd() {
    form = { name: '', vendor: '', size: '', unit_id: '', entry_unit_key: '', category_id: '', tags: [], puc: [] };
    formPhotoFile = null;
    formPhotoPreview = '';
    offBanner = null;
    editModal = { product: null, isNew: true };
  }

  async function openEdit(id) {
    const p = await getProduct(id);
    form = {
      name: p.name || '',
      vendor: p.vendor || '',
      size: p.size || '',
      unit_id: p.unit_id || '',
      entry_unit_key: p.entry_unit_key || '',
      category_id: p.category_id || '',
      tags: [...(p.tags || [])],
      puc: normalizePuc(p.unit_conversions || [])
    };
    formPhotoPreview = p.image_path ? p.image_path : '';
    formPhotoFile = null;
    offBanner = null;
    editModal = { product: p, isNew: false };
  }

  async function saveProduct() {
    const data = {
      name: form.name,
      vendor: form.vendor || null,
      size: form.size || null,
      unit_id: form.unit_id ? Number(form.unit_id) : null,
      entry_unit_key: form.entry_unit_key || null,
      category_id: form.category_id ? Number(form.category_id) : null
    };
    try {
      let saved;
      if (editModal.isNew) {
        saved = await createProduct(data);
        showToast(t('products.toast_created'), 'success');
      } else {
        saved = await updateProduct(editModal.product.id, data);
        showToast(t('products.toast_updated'), 'success');
      }

      // Handle photo upload
      if (formPhotoFile) {
        const fd = new FormData();
        fd.append('file', formPhotoFile);
        await uploadProductImage(saved.id, fd);
      }

      editModal = null;
      await reload();
    } catch (e) {
      showToast(String(e), 'error');
    }
  }

  async function removePhoto() {
    if (!editModal.product) return;
    await deleteProductImage(editModal.product.id);
    formPhotoPreview = '';
    showToast(t('products.toast_photo_removed'), 'success');
    await reload();
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
    eanScannerActive = false;
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

      // Try OpenFoodFacts
      if (editModal?.isNew || editModal) {
        try {
          const info = await getEanInfo(code);
          if (info?.name) offBanner = { code, info };
        } catch {}
      }
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
    eanScannerActive = false;
    addEanCode();
  }

  // OpenFoodFacts
  async function applyOffData(replace) {
    if (!offBanner) return;
    const info = offBanner.info;
    if (replace) {
      form.name = info.name || form.name;
      form.vendor = info.vendor || form.vendor;
      form.size = info.size || form.size;
    }
    if (info.image_url && editModal?.product) {
      try {
        const updated = await setImageFromUrl(editModal.product.id, info.image_url);
        formPhotoPreview = updated?.image_path || '';
        showToast(t('products.off_toast_saved'), 'success');
        await reload();
      } catch {}
    }
    offBanner = null;
  }

  // Tags
  async function addTag(name) {
    if (!editModal?.product) {
      form.tags = [...form.tags, { id: Date.now(), name }];
      return;
    }
    await addTagToProduct(editModal.product.id, name);
    const p = await getProduct(editModal.product.id);
    form.tags = [...(p.tags || [])];
  }

  async function removeTag(name) {
    if (!editModal?.product) {
      form.tags = form.tags.filter(t => t.name !== name);
      return;
    }
    await removeTagFromProduct(editModal.product.id, name);
    const p = await getProduct(editModal.product.id);
    form.tags = [...(p.tags || [])];
  }

  // API returns { unit_name, base_unit, factor } — normalize to { name, to_unit, factor }
  // so UnitConversionEditor can use generic field names
  function normalizePuc(raw) {
    return raw.map(c => ({ ...c, name: c.unit_name, to_unit: c.base_unit }));
  }

  // Unit conversions
  async function addPuc({ factor, to_unit_id, name }) {
    if (!name?.trim()) { showToast(t('products.puc_err_name'), 'error'); return; }
    if (!editModal?.product) return;
    try {
      let resolvedFactor = factor;
      let resolvedBaseUnitId = Number(to_unit_id);

      // If the target is a product-specific conversion (puc_<id>), resolve the chain:
      // e.g. Pack = 6 × Flasche(1.5L) → Pack = 9L, base_unit = L
      if (String(to_unit_id).startsWith('puc_')) {
        const pucId = parseInt(String(to_unit_id).slice(4));
        const ref = form.puc.find(c => c.id === pucId);
        if (!ref) { showToast(t('products.puc_err_unit'), 'error'); return; }
        resolvedFactor = factor * ref.factor;
        resolvedBaseUnitId = ref.base_unit.id;
      }

      await addProductUnitConversion(editModal.product.id, {
        unit_name: name,
        base_unit_id: resolvedBaseUnitId,
        factor: resolvedFactor
      });
      showToast(t('products.puc_toast_added'), 'success');
      const p = await getProduct(editModal.product.id);
      form.puc = normalizePuc(p.unit_conversions || []);
    } catch (e) { showToast(String(e), 'error'); }
  }

  async function removePuc(convId) {
    if (!editModal?.product) return;
    try {
      await deleteProductUnitConversion(editModal.product.id, convId);
      showToast(t('products.puc_toast_removed'), 'success');
      const p = await getProduct(editModal.product.id);
      form.puc = normalizePuc(p.unit_conversions || []);
    } catch (e) { showToast(String(e), 'error'); }
  }

  function handlePhotoFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    formPhotoFile = file;
    formPhotoPreview = URL.createObjectURL(file);
  }
</script>

<div class="px-4 md:px-6 py-5 max-w-5xl">
  <!-- Header -->
  <div class="flex flex-wrap items-center gap-3 mb-5">
    <h1 class="text-xl font-bold text-gray-900 flex-1">{t('products.title')}</h1>
    <button onclick={openAdd}
      class="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 shrink-0">
      <Plus size={16} /> {t('products.btn_add')}
    </button>
  </div>

  <!-- Search -->
  <div class="relative mb-4">
    <Search size={16} class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
    <input bind:value={search} placeholder={t('products.search_placeholder')}
      class="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
  </div>

  {#if loading}
    <div class="flex justify-center py-16 text-gray-400">Loading…</div>
  {:else if filtered.length === 0}
    <p class="text-center text-gray-400 py-12">{t('products.empty')}</p>
  {:else}
    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-gray-200 bg-gray-50">
              <th class="text-left px-4 py-2.5 text-xs font-semibold text-gray-500">{t('products.col_product')}</th>
              <th class="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 hidden sm:table-cell">{t('products.col_size')}</th>
              <th class="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 hidden md:table-cell">{t('products.col_eans')}</th>
              <th class="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 hidden lg:table-cell">{t('products.col_tags')}</th>
              <th class="px-4 py-2.5"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            {#each filtered as p}
              <tr class="hover:bg-gray-50">
                <td class="px-4 py-2.5">
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
                </td>
                <td class="px-4 py-2.5 text-gray-500 hidden sm:table-cell">{p.size ? `${p.size}${p.unit?.abbreviation ? ' ' + p.unit.abbreviation : ''}` : '—'}</td>
                <td class="px-4 py-2.5 hidden md:table-cell">
                  <div class="flex flex-wrap gap-1">
                    {#each p.ean_codes || [] as ean}
                      <span class="text-xs font-mono bg-gray-100 text-gray-600 rounded px-1.5 py-0.5">{ean.code}</span>
                    {/each}
                  </div>
                </td>
                <td class="px-4 py-2.5 hidden lg:table-cell">
                  <div class="flex flex-wrap gap-1">
                    {#each p.tags || [] as tag}
                      <span class="text-xs bg-blue-100 text-blue-700 rounded-full px-2 py-0.5">{tag.name}</span>
                    {/each}
                  </div>
                </td>
                <td class="px-4 py-2.5">
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
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}
</div>

<!-- Edit/Add Modal -->
{#if editModal}
  <Modal title={editModal.isNew ? t('products.modal_add') : t('products.modal_edit')}
    onclose={() => editModal = null} wide>
    <div class="space-y-4">
      <!-- Name -->
      <div>
        <label class="block text-xs font-medium text-gray-700 mb-1">{t('products.label_name')}</label>
        <input bind:value={form.name} placeholder={t('products.placeholder_name')}
          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
      </div>
      <!-- Vendor + Size -->
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1">{t('products.label_vendor')}</label>
          <input bind:value={form.vendor} placeholder={t('products.placeholder_vendor')}
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1">{t('products.label_size')}</label>
          <input bind:value={form.size} placeholder={t('products.placeholder_size')}
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
      </div>
      <!-- Unit + Category -->
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1">{t('products.label_unit')}</label>
          <select bind:value={form.unit_id}
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
            <option value="">{t('common.unit_placeholder')}</option>
            {#each units as u}
              <option value={u.id}>{u.name} ({u.abbreviation})</option>
            {/each}
          </select>
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1">{t('products.label_category')}</label>
          <select bind:value={form.category_id}
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
            <option value="">{t('common.no_category')}</option>
            {#each categories as c}
              <option value={c.id}>{c.name}</option>
            {/each}
          </select>
        </div>
      </div>
      <!-- Entry Unit -->
      {#if entryUnitOptions().length > 0}
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1">{t('products.label_entry_unit')}</label>
          <select bind:value={form.entry_unit_key}
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
            <option value="">{t('products.label_unit')} ({t('common.default')})</option>
            {#each entryUnitOptions() as opt}
              <option value={opt.id}>{opt.label}</option>
            {/each}
          </select>
          <p class="mt-1 text-xs text-gray-400">{t('products.label_entry_unit_hint')}</p>
        </div>
      {/if}
      <!-- Photo -->
      <div>
        <label class="block text-xs font-medium text-gray-700 mb-1">{t('products.label_photo')}</label>
        {#if formPhotoPreview}
          <div class="flex items-center gap-3">
            <img src={formPhotoPreview} alt="" class="w-16 h-16 rounded-lg object-cover" />
            <button onclick={removePhoto} class="text-xs text-red-600 hover:underline">{t('products.btn_remove_photo')}</button>
          </div>
        {:else}
          <input type="file" accept="image/*" onchange={handlePhotoFile}
            class="text-sm text-gray-500" />
        {/if}
      </div>
      <!-- OFF Banner -->
      {#if offBanner}
        <div class="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm">
          <p class="font-medium text-amber-800">{t('products.off_banner_label')}: {offBanner.info.name}</p>
          <div class="flex gap-2 mt-2">
            <button onclick={() => applyOffData(true)}
              class="px-3 py-1 text-xs bg-amber-600 text-white rounded-md hover:bg-amber-700">
              {t('products.off_btn_replace')}
            </button>
            <button onclick={() => offBanner = null}
              class="px-3 py-1 text-xs border border-gray-300 rounded-md hover:bg-gray-50">
              {t('products.off_btn_dismiss')}
            </button>
          </div>
        </div>
      {/if}
      <!-- Tags -->
      <div>
        <label class="block text-xs font-medium text-gray-700 mb-1">{t('common.tags_label')}</label>
        <TagChips tags={form.tags} onadd={addTag} onremove={removeTag} />
      </div>
      <!-- Unit Conversions -->
      {#if !editModal.isNew && editModal.product}
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-2">{t('products.puc_label')}</label>
          <UnitConversionEditor
            conversions={form.puc}
            units={units}
            pucUnits={form.puc}
            withName={true}
            onadd={addPuc}
            onremove={removePuc} />
        </div>
      {/if}
      <!-- Actions -->
      <div class="flex justify-end gap-2 pt-2 border-t border-gray-100">
        <button onclick={() => editModal = null}
          class="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
          {t('common.cancel')}
        </button>
        <button onclick={saveProduct}
          class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium">
          {editModal.isNew ? t('common.create') : t('common.save')}
        </button>
      </div>
    </div>
  </Modal>
{/if}

<!-- EAN Modal -->
{#if eanModal}
  <Modal title={t('products.ean_modal_title')} onclose={() => { eanModal = null; eanScannerActive = false; }}>
    <div class="space-y-4">
      <p class="text-sm text-gray-500">{t('products.ean_modal_hint')}</p>
      <!-- Existing EANs -->
      {#if eanList.length > 0}
        <div class="flex flex-wrap gap-2">
          {#each eanList as ean}
            <span class="inline-flex items-center gap-1.5 font-mono text-xs bg-gray-100 rounded-md px-2.5 py-1">
              {ean.code}
              <button onclick={() => removeEanCode(ean.id)} class="text-gray-400 hover:text-red-600">
                <X size={12} />
              </button>
            </span>
          {/each}
        </div>
      {/if}
      <!-- Scanner -->
      {#if eanScannerActive}
        <BarcodeScanner active={true} onscan={handleEanScan} />
        <button onclick={() => eanScannerActive = false}
          class="w-full py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
          {t('products.ean_btn_stop')}
        </button>
      {:else}
        <div class="flex gap-2">
          <input bind:value={eanInput} placeholder={t('products.ean_placeholder')}
            onkeydown={(e) => e.key === 'Enter' && addEanCode()}
            class="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <button onclick={addEanCode} class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            {t('common.add')}
          </button>
          <button onclick={() => eanScannerActive = true}
            class="px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
            <Barcode size={16} />
          </button>
        </div>
      {/if}
      <div class="flex justify-end pt-1">
        <button onclick={() => { eanModal = null; eanScannerActive = false; reload(); }}
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
