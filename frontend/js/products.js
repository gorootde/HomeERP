import { getProducts, createProduct, updateProduct, deleteProduct, addEan, removeEan, uploadProductImage, deleteProductImage, setImageFromUrl, getTags, addTagToProduct, removeTagFromProduct, getUnits, getCategories, getEanInfo, addProductUnitConversion, deleteProductUnitConversion } from './api.js';
import { openModal, openConfirm, showToast, escHtml, fmtFactor, buildUnitOptions, renderTagChips, buildTagsSection, attachTagListeners } from './app.js';
import { t } from './i18n.js';

let _allProducts = [];
let _allTags = [];
let _allUnits = [];
let _allCategories = [];

export async function render() {
  const content  = document.getElementById('app-content');
  [_allProducts, _allTags, _allUnits, _allCategories] = await Promise.all([getProducts(), getTags(), getUnits(), getCategories()]);
  renderTable(content, _allProducts);
}

function productThumb(p) {
  if (p.image_path) {
    return `<img class="product-thumb" src="${escHtml(p.image_path)}" alt="${escHtml(p.name)}" />`;
  }
  return `<span class="product-thumb-placeholder"><i data-lucide="image"></i></span>`;
}

function renderTable(content, products) {
  const rows = products.map(p => {
    const eans = p.ean_codes.map(e =>
      `<span class="ean-tag font-mono">${escHtml(e.code)}</span>`
    ).join('');

    return `
      <tr>
        <td>
          <div class="product-cell">
            ${productThumb(p)}
            <div>
              <div class="font-semibold">${escHtml(p.name)}</div>
              <div class="text-muted text-sm">${escHtml(p.vendor)}</div>
            </div>
          </div>
        </td>
        <td class="text-muted">${escHtml(p.size)}${p.unit ? ' ' + escHtml(p.unit.abbreviation) : ''}</td>
        <td><div class="ean-tags">${eans || '<span class="text-muted text-sm">—</span>'}</div></td>
        <td><div class="item-tags">${renderTagChips(p.tags)}</div></td>
        <td>
          <div class="td-actions">
            <button class="btn btn-ghost btn-sm" data-edit="${p.id}">
              <i data-lucide="pencil"></i> ${t('common.edit')}
            </button>
            <button class="btn btn-ghost btn-sm" data-eans="${p.id}">
              <i data-lucide="barcode"></i> ${t('products.btn_eans')}
            </button>
            <button class="btn btn-danger btn-sm" data-delete="${p.id}" data-name="${escHtml(p.name)}">
              <i data-lucide="trash-2"></i>
            </button>
          </div>
        </td>
      </tr>`;
  }).join('');

  const emptyRow = `
    <tr><td colspan="5">
      <div class="empty-state"><i data-lucide="boxes"></i><p>${t('products.empty')}</p></div>
    </td></tr>`;

  content.innerHTML = `
    <div class="page-header">
      <h1 class="page-title">${t('products.title')}</h1>
      <div class="page-header-actions">
        <div class="search-bar">
          <i data-lucide="search"></i>
          <input id="prod-search" type="search" placeholder="${t('products.search_placeholder')}" />
        </div>
        <button class="btn btn-primary" id="btn-add-product">
          <i data-lucide="plus"></i> ${t('products.btn_add')}
        </button>
      </div>
    </div>
    <div class="table-container">
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>${t('products.col_product')}</th>
              <th>${t('products.col_size')}</th>
              <th>${t('products.col_eans')}</th>
              <th>${t('products.col_tags')}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>${rows || emptyRow}</tbody>
        </table>
      </div>
    </div>`;

  // ── Search ───────────────────────────────────────────────────────────────
  document.getElementById('prod-search').addEventListener('input', e => {
    const q   = e.target.value.toLowerCase();
    const filtered = _allProducts.filter(p =>
      p.name.toLowerCase().includes(q) || p.vendor.toLowerCase().includes(q)
    );
    const tbody = content.querySelector('tbody');
    tbody.innerHTML = filtered.map(p => {
      const eans = p.ean_codes.map(e =>
        `<span class="ean-tag font-mono">${escHtml(e.code)}</span>`
      ).join('');
      return `
        <tr>
          <td>
            <div class="product-cell">
              ${productThumb(p)}
              <div>
                <div class="font-semibold">${escHtml(p.name)}</div>
                <div class="text-muted text-sm">${escHtml(p.vendor)}</div>
              </div>
            </div>
          </td>
          <td class="text-muted">${escHtml(p.size)}${p.unit ? ' ' + escHtml(p.unit.abbreviation) : ''}</td>
          <td><div class="ean-tags">${eans || '<span class="text-muted text-sm">—</span>'}</div></td>
          <td><div class="item-tags">${renderTagChips(p.tags)}</div></td>
          <td>
            <div class="td-actions">
              <button class="btn btn-ghost btn-sm" data-edit="${p.id}"><i data-lucide="pencil"></i> ${t('common.edit')}</button>
              <button class="btn btn-ghost btn-sm" data-eans="${p.id}"><i data-lucide="barcode"></i> ${t('products.btn_eans')}</button>
              <button class="btn btn-danger btn-sm" data-delete="${p.id}" data-name="${escHtml(p.name)}"><i data-lucide="trash-2"></i></button>
            </div>
          </td>
        </tr>`;
    }).join('') || emptyRow;
    lucide.createIcons();
    attachRowListeners(content);
  });

  document.getElementById('btn-add-product').addEventListener('click', () => showProductModal(null));
  attachRowListeners(content);
}

function attachRowListeners(content) {
  content.querySelectorAll('[data-edit]').forEach(btn => {
    const product = _allProducts.find(p => p.id === Number(btn.dataset.edit));
    btn.addEventListener('click', () => product && showProductModal(product));
  });

  content.querySelectorAll('[data-eans]').forEach(btn => {
    const product = _allProducts.find(p => p.id === Number(btn.dataset.eans));
    btn.addEventListener('click', () => product && showEanModal(product));
  });

  content.querySelectorAll('[data-delete]').forEach(btn => {
    const id   = Number(btn.dataset.delete);
    const name = btn.dataset.name;
    btn.addEventListener('click', () => {
      openConfirm(t('products.confirm_delete', { name }), async () => {
        try {
          await deleteProduct(id);
          showToast(t('products.toast_deleted'));
          render();
        } catch (err) {
          showToast(err.message, 'error');
        }
      });
    });
  });
}

function buildCategoryOptions(selectedId) {
  const none = `<option value=""${!selectedId ? ' selected' : ''}>${t('common.no_category')}</option>`;
  const opts = _allCategories.map(c =>
    `<option value="${c.id}"${c.id === selectedId ? ' selected' : ''}>${escHtml(c.name)}</option>`
  ).join('');
  return none + opts;
}

function showProductModal(product) {
  const isEdit = !!product;
  const hasImage = isEdit && !!product.image_path;

  const imageSection = isEdit ? `
    <div class="form-field">
      <label>${t('products.label_photo')}</label>
      <div class="image-upload-area" id="img-upload-area">
        ${hasImage
          ? `<img id="img-preview" class="image-preview" src="${escHtml(product.image_path)}" alt="${t('products.label_photo')}" />`
          : `<div id="img-placeholder" class="image-placeholder"><i data-lucide="image-plus"></i><span>${t('products.photo_placeholder')}</span></div>`
        }
        <input id="pf-image" type="file" accept="image/*" class="image-file-input" />
      </div>
      ${hasImage ? `<button type="button" class="btn btn-ghost btn-sm mt-2" id="btn-remove-img"><i data-lucide="trash-2"></i> ${t('products.btn_remove_photo')}</button>` : ''}
    </div>` : '';

  const tagsSection = isEdit ? buildTagsSection(product.tags) : '';
  const unitConversionsSection = isEdit ? buildUnitConversionsSection(product.unit_conversions || []) : '';

  const { overlay, close } = openModal(
    isEdit ? t('products.modal_edit') : t('products.modal_add'),
    `<form id="prod-form">
       <div class="form-row">
         <div class="form-field">
           <label for="pf-vendor">${t('products.label_vendor')}</label>
           <input id="pf-vendor" name="vendor" type="text" required placeholder="${t('products.placeholder_vendor')}"
             value="${isEdit ? escHtml(product.vendor) : ''}" />
         </div>
         <div class="form-field">
           <label for="pf-size">${t('products.label_size')}</label>
           <input id="pf-size" name="size" type="number" min="0" step="any" required placeholder="${t('products.placeholder_size')}"
             value="${isEdit ? escHtml(product.size) : ''}" />
         </div>
       </div>
       <div class="form-row">
         <div class="form-field">
           <label for="pf-unit">${t('products.label_unit')}</label>
           <select id="pf-unit" name="unit_id" required>
             ${buildUnitOptions(_allUnits, isEdit ? product.unit_id : null)}
           </select>
         </div>
         <div class="form-field">
           <label for="pf-category">${t('products.label_category')}</label>
           <select id="pf-category" name="category_id">
             ${buildCategoryOptions(isEdit ? product.category_id : null)}
           </select>
         </div>
       </div>
       <div class="form-field">
         <label for="pf-name">${t('products.label_name')}</label>
         <input id="pf-name" name="name" type="text" required placeholder="${t('products.placeholder_name')}"
           value="${isEdit ? escHtml(product.name) : ''}" />
       </div>
       ${unitConversionsSection}
       ${tagsSection}
       ${imageSection}
       <div class="form-actions">
         <button type="button" class="btn btn-ghost" id="pf-cancel">${t('common.cancel')}</button>
         <button type="submit" class="btn btn-primary">${isEdit ? t('common.save') : t('common.create')}</button>
       </div>
     </form>`
  );
  lucide.createIcons();

  // Tag management
  if (isEdit) {
    attachTagListeners(overlay, product.tags, product.id, addTagToProduct, removeTagFromProduct, _allTags);
  }

  // Product-specific unit conversions
  if (isEdit) {
    attachUnitConversionListeners(overlay, product.unit_conversions || [], product.id);
  }

  // Image upload preview
  if (isEdit) {
    const fileInput = overlay.querySelector('#pf-image');
    const uploadArea = overlay.querySelector('#img-upload-area');

    fileInput.addEventListener('change', () => {
      const file = fileInput.files[0];
      if (!file) return;
      const url = URL.createObjectURL(file);
      uploadArea.innerHTML = `<img id="img-preview" class="image-preview" src="${url}" alt="Preview" /><input id="pf-image" type="file" accept="image/*" class="image-file-input" />`;
      uploadArea.querySelector('#pf-image').addEventListener('change', arguments.callee);
    });

    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', e => { e.preventDefault(); uploadArea.classList.add('drag-over'); });
    uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('drag-over'));
    uploadArea.addEventListener('drop', e => {
      e.preventDefault();
      uploadArea.classList.remove('drag-over');
      const file = e.dataTransfer.files[0];
      if (!file || !file.type.startsWith('image/')) return;
      fileInput.files = e.dataTransfer.files;
      const url = URL.createObjectURL(file);
      uploadArea.innerHTML = `<img id="img-preview" class="image-preview" src="${url}" alt="Preview" /><input id="pf-image" type="file" accept="image/*" class="image-file-input" />`;
    });

    const removeBtn = overlay.querySelector('#btn-remove-img');
    if (removeBtn) {
      removeBtn.addEventListener('click', async () => {
        try {
          await deleteProductImage(product.id);
          showToast(t('products.toast_photo_removed'));
          close();
          render();
        } catch (err) {
          showToast(err.message, 'error');
        }
      });
    }
  }

  overlay.querySelector('#pf-cancel').addEventListener('click', close);
  overlay.querySelector('#prod-form').addEventListener('submit', async e => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const unitVal = fd.get('unit_id');
    const catVal  = fd.get('category_id');
    const data = {
      vendor:      fd.get('vendor'),
      name:        fd.get('name'),
      size:        fd.get('size'),
      unit_id:     Number(unitVal),
      category_id: catVal  ? Number(catVal)  : null,
    };
    try {
      if (isEdit) {
        await updateProduct(product.id, data);
        const fileInput = overlay.querySelector('#pf-image');
        if (fileInput && fileInput.files[0]) {
          await uploadProductImage(product.id, fileInput.files[0]);
        }
        showToast(t('products.toast_updated'));
      } else {
        await createProduct(data);
        showToast(t('products.toast_created'));
      }
      close();
      render();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  overlay.querySelector('#pf-name').focus();
}

function showEanModal(product) {
  const buildEanList = (eans) =>
    eans.map(e => `
      <span class="ean-tag" data-ean-id="${e.id}">
        ${escHtml(e.code)}
        <button type="button" title="Remove" data-remove-ean="${e.id}">
          <i data-lucide="x"></i>
        </button>
      </span>`).join('');

  const { overlay, close } = openModal(
    t('products.ean_modal_title', { name: escHtml(product.name) }),
    `<p class="text-muted text-sm mb-4">${t('products.ean_modal_hint')}</p>
     <div class="ean-manager">
       <div class="ean-manager-list" id="ean-list">${buildEanList(product.ean_codes)}</div>
       <div class="ean-add-row">
         <input id="ean-input" type="text" placeholder="${t('products.ean_placeholder')}" inputmode="numeric" />
         <button type="button" class="btn btn-ghost btn-sm" id="btn-scan-ean" title="${t('products.btn_eans')}">
           <i data-lucide="scan-barcode"></i>
         </button>
         <button type="button" class="btn btn-primary btn-sm" id="btn-add-ean">
           <i data-lucide="plus"></i> ${t('common.add')}
         </button>
       </div>
       <div id="ean-scanner-container" style="display:none;margin-top:12px">
         <div id="ean-qr-reader"></div>
         <button type="button" class="btn btn-ghost btn-sm" id="btn-stop-ean-scan" style="margin-top:8px">
           <i data-lucide="x"></i> ${t('products.ean_btn_stop')}
         </button>
       </div>
     </div>
     <div id="off-suggestion"></div>
     <div class="form-actions" style="margin-top:16px">
       <button type="button" class="btn btn-ghost" id="ean-done">${t('products.ean_btn_done')}</button>
     </div>`
  );
  lucide.createIcons();

  const eanList  = overlay.querySelector('#ean-list');
  const eanInput = overlay.querySelector('#ean-input');
  let   eans     = [...product.ean_codes];

  // ── EAN scanner ───────────────────────────────────────────────────────────
  let _eanScanner = null;

  const stopEanScanner = async () => {
    if (_eanScanner) {
      try { if (_eanScanner.isScanning) await _eanScanner.stop(); } catch (_) {}
      _eanScanner = null;
    }
    const container = overlay.querySelector('#ean-scanner-container');
    if (container) container.style.display = 'none';
  };

  overlay.querySelector('#btn-scan-ean').addEventListener('click', async () => {
    if (!window.Html5Qrcode) { showToast(t('common.scanner_unavailable'), 'error'); return; }
    const container = overlay.querySelector('#ean-scanner-container');
    container.style.display = 'block';
    _eanScanner = new Html5Qrcode('ean-qr-reader');
    try {
      await _eanScanner.start(
        { facingMode: 'environment' },
        { fps: 10, qrbox: { width: 260, height: 120 } },
        async (decodedText) => {
          await stopEanScanner();
          eanInput.value = decodedText;
          eanInput.focus();
        },
        () => {}
      );
    } catch (_) {
      showToast(t('common.camera_unavailable'), 'error');
      _eanScanner = null;
      container.style.display = 'none';
    }
  });

  overlay.querySelector('#btn-stop-ean-scan').addEventListener('click', stopEanScanner);

  // Stop the scanner whenever the modal is closed via X button or background click
  overlay.querySelector('.modal-close').addEventListener('click', () => stopEanScanner());
  overlay.addEventListener('click', e => { if (e.target === overlay) stopEanScanner(); });

  const refreshList = () => {
    eanList.innerHTML = buildEanList(eans);
    lucide.createIcons({ nodes: [eanList] });
    attachRemoveListeners();
  };

  const attachRemoveListeners = () => {
    eanList.querySelectorAll('[data-remove-ean]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const eanId = Number(btn.dataset.removeEan);
        try {
          await removeEan(product.id, eanId);
          eans = eans.filter(e => e.id !== eanId);
          refreshList();
          showToast(t('products.ean_toast_removed'));
        } catch (err) {
          showToast(err.message, 'error');
        }
      });
    });
  };
  attachRemoveListeners();

  const addEanHandler = async () => {
    const code = eanInput.value.trim();
    if (!code) return;
    try {
      const newEan = await addEan(product.id, code);
      eans.push(newEan);
      eanInput.value = '';
      refreshList();
      showToast(t('products.ean_toast_added'));
      lookupAndSuggestImage(product, code, overlay);
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  overlay.querySelector('#btn-add-ean').addEventListener('click', addEanHandler);
  eanInput.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); addEanHandler(); } });
  overlay.querySelector('#ean-done').addEventListener('click', async () => { await stopEanScanner(); close(); render(); });
  eanInput.focus();
}

// ── OpenFoodFacts lookup ──────────────────────────────────────────────────────

async function lookupAndSuggestImage(product, barcode, overlay) {
  const box = overlay.querySelector('#off-suggestion');
  if (!box) return;
  box.innerHTML = `<div class="off-suggestion off-suggestion--loading"><i data-lucide="loader-circle" class="spin"></i> ${t('products.off_loading')}</div>`;
  lucide.createIcons({ nodes: [box] });

  const info = await getEanInfo(barcode).catch(() => null);
  const imageUrl = info?.image_url || null;
  if (!imageUrl) { box.innerHTML = ''; return; }

  const hasImage = !!product.image_path;
  box.innerHTML = `
    <div class="off-suggestion">
      <img class="off-suggestion__thumb" src="${escHtml(imageUrl)}" alt="${t('products.off_found')}" />
      <div class="off-suggestion__body">
        <p class="off-suggestion__title">${t('products.off_found')}</p>
        <p class="text-muted text-sm">${hasImage ? t('products.off_replace_q') : t('products.off_use_q')}</p>
        <div class="off-suggestion__actions">
          <button type="button" class="btn btn-primary btn-sm" id="off-accept">
            <i data-lucide="image-plus"></i> ${hasImage ? t('products.off_btn_replace') : t('products.off_btn_use')}
          </button>
          <button type="button" class="btn btn-ghost btn-sm" id="off-dismiss">${t('products.off_btn_dismiss')}</button>
        </div>
      </div>
    </div>`;
  lucide.createIcons({ nodes: [box] });

  box.querySelector('#off-dismiss').addEventListener('click', () => { box.innerHTML = ''; });
  box.querySelector('#off-accept').addEventListener('click', async () => {
    box.innerHTML = `<div class="off-suggestion off-suggestion--loading"><i data-lucide="loader-circle" class="spin"></i> ${t('products.off_saving')}</div>`;
    lucide.createIcons({ nodes: [box] });
    try {
      await setImageFromUrl(product.id, imageUrl);
      product.image_path = imageUrl; // mark as having an image for future suggestions
      box.innerHTML = `<div class="off-suggestion off-suggestion--success"><i data-lucide="circle-check"></i> ${t('products.off_saved')}</div>`;
      lucide.createIcons({ nodes: [box] });
      showToast(t('products.off_toast_saved'));
    } catch (err) {
      showToast(err.message, 'error');
      box.innerHTML = '';
    }
  });
}

// ── Product unit conversion helpers ──────────────────────────────────────────

function buildUnitConversionList(conversions) {
  if (!conversions || conversions.length === 0) {
    return `<p class="text-muted text-sm" id="puc-empty">${t('products.puc_empty')}</p>`;
  }
  return conversions.map(c => {
    const factorStr = fmtFactor(c.factor);
    return `
      <div class="puc-entry" data-conv-id="${c.id}">
        <span class="puc-label">1 <strong>${escHtml(c.unit_name)}</strong> = ${escHtml(factorStr)} ${escHtml(c.base_unit.abbreviation)}</span>
        <button type="button" class="btn btn-ghost btn-sm" data-remove-conv="${c.id}" title="Entfernen">
          <i data-lucide="x"></i>
        </button>
      </div>`;
  }).join('');
}

function buildUnitConversionsSection(conversions) {
  return `
    <div class="form-field">
      <label>${t('products.puc_label')}</label>
      <div class="puc-manager">
        <div id="puc-list">${buildUnitConversionList(conversions)}</div>
        <div class="puc-add-row">
          <input id="puc-name" type="text" placeholder="${t('products.puc_name_placeholder')}" style="flex:1.2" />
          <span class="puc-equals">=</span>
          <input id="puc-factor" type="number" min="0.000001" step="any" placeholder="1.5" style="flex:0.7" />
          <select id="puc-unit" style="flex:1">
            ${buildUnitOptions(_allUnits, null)}
          </select>
          <button type="button" class="btn btn-ghost btn-sm" id="btn-add-puc" title="Hinzufügen">
            <i data-lucide="plus"></i>
          </button>
        </div>
        <p class="text-muted text-sm" id="puc-preview" style="margin-top:4px"></p>
      </div>
    </div>`;
}

function attachUnitConversionListeners(overlay, initialConversions, productId) {
  const list    = overlay.querySelector('#puc-list');
  const nameIn  = overlay.querySelector('#puc-name');
  const factorIn = overlay.querySelector('#puc-factor');
  const unitSel = overlay.querySelector('#puc-unit');
  const preview = overlay.querySelector('#puc-preview');
  if (!list) return;

  let conversions = [...initialConversions];

  const updatePreview = () => {
    const name   = nameIn.value.trim();
    const factor = parseFloat(factorIn.value);
    const selOpt = unitSel.options[unitSel.selectedIndex];
    if (name && factor > 0 && unitSel.value) {
      const abbr = selOpt ? selOpt.text.match(/\(([^)]+)\)$/)?.[1] ?? '' : '';
      preview.textContent = `1 ${name} = ${factor} ${abbr}`;
    } else {
      preview.textContent = '';
    }
  };

  nameIn.addEventListener('input', updatePreview);
  factorIn.addEventListener('input', updatePreview);
  unitSel.addEventListener('change', updatePreview);

  const refreshList = () => {
    list.innerHTML = buildUnitConversionList(conversions);
    lucide.createIcons({ nodes: [list] });
    attachRemoveListeners();
  };

  const attachRemoveListeners = () => {
    list.querySelectorAll('[data-remove-conv]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const convId = Number(btn.dataset.removeConv);
        try {
          await deleteProductUnitConversion(productId, convId);
          conversions = conversions.filter(c => c.id !== convId);
          refreshList();
          showToast(t('products.puc_toast_removed'));
        } catch (err) {
          showToast(err.message, 'error');
        }
      });
    });
  };
  attachRemoveListeners();

  overlay.querySelector('#btn-add-puc').addEventListener('click', async () => {
    const unit_name    = nameIn.value.trim();
    const factor       = parseFloat(factorIn.value);
    const base_unit_id = Number(unitSel.value);
    if (!unit_name)       { showToast(t('products.puc_err_name'), 'error'); return; }
    if (!(factor > 0))    { showToast(t('products.puc_err_factor'), 'error'); return; }
    if (!base_unit_id)    { showToast(t('products.puc_err_unit'), 'error'); return; }
    try {
      const conv = await addProductUnitConversion(productId, { unit_name, base_unit_id, factor });
      conversions.push(conv);
      nameIn.value = '';
      factorIn.value = '';
      unitSel.value = '';
      preview.textContent = '';
      refreshList();
      showToast(t('products.puc_toast_added'));
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

