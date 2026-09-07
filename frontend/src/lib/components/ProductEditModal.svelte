<script>
  import { onMount } from 'svelte';
  import { t } from '$lib/i18n.svelte.js';
  import { showToast } from '$lib/toast.js';
  import {
    getProduct, createProduct, updateProduct,
    setImageFromUrl, uploadProductImage, deleteProductImage,
    addTagToProduct, removeTagFromProduct,
    addProductUnitConversion, deleteProductUnitConversion
  } from '$lib/api.js';
  import { matchUnitFromOffSize, resolveUnitConversion, stagePucConversion } from '$lib/utils.js';
  import { useTags } from '$lib/useTags.js';
  import Modal from './Modal.svelte';
  import TagChips from './TagChips.svelte';
  import UnitConversionEditor from './UnitConversionEditor.svelte';

  /**
   * Product create/edit dialog, shared by the products list and the stock list.
   *
   * Props:
   *   productId  — id of the product to edit, or null/undefined to create a new one
   *   units      — global units list
   *   categories — categories list
   *   onsaved(product) — called after a successful create/update (parent reloads/closes)
   *   onclose()  — cancel / dismiss
   */
  let { productId = null, units = [], categories = [], onsaved, onclose } = $props();

  const isNew = productId == null;

  let loading = $state(!isNew);
  let product = $state(null); // the loaded product row (edit mode)

  let form = $state({ name: '', vendor: '', unit_id: '', entry_unit_key: '', category_id: '', tags: [], puc: [] });
  let formPhotoFile = $state(null);
  let formPhotoPreview = $state('');
  let offBanner = $state(null);

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

  onMount(async () => {
    if (isNew) return;
    try {
      const p = await getProduct(productId);
      product = p;
      form = {
        name: p.name || '',
        vendor: p.vendor || '',
        unit_id: p.unit_id || '',
        entry_unit_key: p.entry_unit_key || '',
        category_id: p.category_id || '',
        tags: [...(p.tags || [])],
        puc: normalizePuc(p.unit_conversions || [])
      };
      formPhotoPreview = p.image_path ? p.image_path : '';
    } catch (e) {
      showToast(String(e), 'error');
      onclose?.();
    } finally {
      loading = false;
    }
  });

  async function saveProduct() {
    // A staged puc row's id (e.g. 'staged-...') isn't a real conversion id yet, so an
    // entry_unit_key referencing one via 'puc_<id>' can't be sent until that row is
    // persisted below — remember it and resolve it afterwards instead.
    const stagedEntryKey = isNew && form.entry_unit_key?.startsWith('puc_')
      && form.puc.some(c => String(c.id) === form.entry_unit_key.slice(4))
      ? form.entry_unit_key
      : null;

    const data = {
      name: form.name,
      vendor: form.vendor || null,
      unit_id: form.unit_id ? Number(form.unit_id) : null,
      entry_unit_key: stagedEntryKey ? null : (form.entry_unit_key || null),
      category_id: form.category_id ? Number(form.category_id) : null
    };
    try {
      let saved;
      if (isNew) {
        saved = await createProduct(data);
        for (const puc of form.puc) {
          const created = await addProductUnitConversion(saved.id, {
            unit_name: puc.unit_name,
            base_unit_id: puc.base_unit_id,
            factor: puc.factor
          });
          if (stagedEntryKey && String(puc.id) === stagedEntryKey.slice(4)) {
            await updateProduct(saved.id, { entry_unit_key: 'puc_' + created.id });
          }
        }
        showToast(t('products.toast_created'), 'success');
      } else {
        saved = await updateProduct(product.id, data);
        showToast(t('products.toast_updated'), 'success');
      }

      // Handle photo upload
      if (formPhotoFile) {
        const fd = new FormData();
        fd.append('file', formPhotoFile);
        await uploadProductImage(saved.id, fd);
      }

      onsaved?.(saved);
    } catch (e) {
      showToast(String(e), 'error');
    }
  }

  async function removePhoto() {
    if (!product) return;
    await deleteProductImage(product.id);
    formPhotoPreview = '';
    showToast(t('products.toast_photo_removed'), 'success');
    onsaved?.(product);
  }

  // Tags
  const { addTag, removeTag } = useTags(() => form, {
    getEntityId: () => product?.id,
    addFn: addTagToProduct,
    removeFn: removeTagFromProduct,
    fetchTags: async (id) => (await getProduct(id)).tags || [],
  });

  // OpenFoodFacts (banner is only surfaced by callers that also manage EANs)
  async function applyOffData(replace) {
    if (!offBanner) return;
    const info = offBanner.info;
    if (replace) {
      form.name = info.name || form.name;
      form.vendor = info.vendor || form.vendor;
      const { numeric, matchedUnit } = matchUnitFromOffSize(units, info.size);
      if (matchedUnit) form.unit_id = matchedUnit.id;
      const baseUnitId = matchedUnit?.id ?? (form.unit_id ? Number(form.unit_id) : null);
      if (numeric && baseUnitId) {
        await addPuc({ factor: parseFloat(numeric), to_unit_id: baseUnitId, name: t('common.unit_piece_label') });
      }
    }
    if (info.image_url && product) {
      try {
        const updated = await setImageFromUrl(product.id, info.image_url);
        formPhotoPreview = updated?.image_path || '';
        showToast(t('products.off_toast_saved'), 'success');
      } catch {}
    }
    offBanner = null;
  }

  // API returns { unit_name, base_unit, factor } — normalize to { name, to_unit, factor }
  // so UnitConversionEditor can use generic field names
  function normalizePuc(raw) {
    return raw.map(c => ({ ...c, name: c.unit_name, to_unit: c.base_unit }));
  }

  // Unit conversions — while creating a new product there's no product id yet to
  // POST conversions against, so they're staged locally (stagePucConversion) and
  // persisted in saveProduct() once the product itself has been created.
  async function addPuc({ factor, to_unit_id, name }) {
    if (!name?.trim()) { showToast(t('products.puc_err_name'), 'error'); return; }

    if (isNew) {
      const staged = stagePucConversion({ factor, to_unit_id, name, units, pucUnits: form.puc });
      if (!staged) { showToast(t('products.puc_err_unit'), 'error'); return; }
      form.puc = [...form.puc, staged];
      return;
    }

    if (!product) return;
    try {
      const resolved = resolveUnitConversion({ factor, to_unit_id, units, pucUnits: form.puc });
      if (!resolved) { showToast(t('products.puc_err_unit'), 'error'); return; }

      await addProductUnitConversion(product.id, {
        unit_name: name,
        base_unit_id: resolved.base_unit_id,
        factor: resolved.factor
      });
      showToast(t('products.puc_toast_added'), 'success');
      const p = await getProduct(product.id);
      form.puc = normalizePuc(p.unit_conversions || []);
    } catch (e) { showToast(String(e), 'error'); }
  }

  async function removePuc(convId) {
    if (isNew) {
      form.puc = form.puc.filter(c => c.id !== convId);
      return;
    }
    if (!product) return;
    try {
      await deleteProductUnitConversion(product.id, convId);
      showToast(t('products.puc_toast_removed'), 'success');
      const p = await getProduct(product.id);
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

<Modal title={isNew ? t('products.modal_add') : t('products.modal_edit')} onclose={onclose} wide>
  {#if loading}
    <div class="py-12 text-center text-gray-400">{t('common.loading')}</div>
  {:else}
    <div class="space-y-4">
      <!-- Name -->
      <div>
        <label class="block text-xs font-medium text-gray-700 mb-1">{t('products.label_name')}</label>
        <input bind:value={form.name} placeholder={t('products.placeholder_name')}
          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
      </div>
      <!-- Vendor -->
      <div>
        <label class="block text-xs font-medium text-gray-700 mb-1">{t('products.label_vendor')}</label>
        <input bind:value={form.vendor} placeholder={t('products.placeholder_vendor')}
          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
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
      {#if form.unit_id}
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
        <button onclick={onclose}
          class="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
          {t('common.cancel')}
        </button>
        <button onclick={saveProduct}
          class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium">
          {isNew ? t('common.create') : t('common.save')}
        </button>
      </div>
    </div>
  {/if}
</Modal>
