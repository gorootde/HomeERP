const BASE = '/api';

async function request(method, path, body = null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body !== null) opts.body = JSON.stringify(body);
  const res = await fetch(BASE + path, opts);
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({ detail: res.statusText }));
  if (!res.ok) {
    const msg = data?.detail ?? `HTTP ${res.status}`;
    throw Object.assign(new Error(Array.isArray(msg) ? msg.map(e => e.msg).join(', ') : msg), { status: res.status });
  }
  return data;
}

// ── Products ────────────────────────────────────────────────────────────────
export const getProducts   = (search = '') => request('GET', `/products?search=${encodeURIComponent(search)}&limit=500`);
export const getProduct    = (id)          => request('GET', `/products/${id}`);
export const createProduct = (data)        => request('POST', '/products', data);
export const updateProduct = (id, data)    => request('PUT', `/products/${id}`, data);
export const deleteProduct = (id)          => request('DELETE', `/products/${id}`);
export const addEan             = (id, code)    => request('POST', `/products/${id}/ean`, { code });
export const removeEan          = (id, eanId)   => request('DELETE', `/products/${id}/ean/${eanId}`);
export const getByEan           = (ean)         => request('GET', `/products/by-ean/${encodeURIComponent(ean)}`);
export const setImageFromUrl    = (id, url)     => request('POST', `/products/${id}/image-from-url`, { url });

export async function uploadProductImage(id, file) {
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch(`${BASE}/products/${id}/image`, { method: 'POST', body: fd });
  const data = await res.json().catch(() => ({ detail: res.statusText }));
  if (!res.ok) throw new Error(data?.detail ?? `HTTP ${res.status}`);
  return data;
}

export async function deleteProductImage(id) {
  const res = await fetch(`${BASE}/products/${id}/image`, { method: 'DELETE' });
  if (!res.ok) {
    const data = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(data?.detail ?? `HTTP ${res.status}`);
  }
}

// ── Vaults ──────────────────────────────────────────────────────────────────
export const getVaults    = ()         => request('GET', '/vaults');
export const createVault  = (data)     => request('POST', '/vaults', data);
export const updateVault  = (id, data) => request('PUT', `/vaults/${id}`, data);
export const deleteVault  = (id)       => request('DELETE', `/vaults/${id}`);

// ── Tags ────────────────────────────────────────────────────────────────────
export const getTags = () => request('GET', '/tags');

export const addTagToProduct     = (id, name) => request('POST', `/products/${id}/tags`, { name });
export const removeTagFromProduct = (id, name) => request('DELETE', `/products/${id}/tags/${encodeURIComponent(name)}`);

export const addTagToVault       = (id, name) => request('POST', `/vaults/${id}/tags`, { name });
export const removeTagFromVault  = (id, name) => request('DELETE', `/vaults/${id}/tags/${encodeURIComponent(name)}`);

export const addTagToStockEntry      = (id, name)       => request('POST',   `/stock/entries/${id}/tags`, { name });
export const removeTagFromStockEntry = (id, name)       => request('DELETE', `/stock/entries/${id}/tags/${encodeURIComponent(name)}`);

export const addStockId              = (id, code)       => request('POST',   `/stock/entries/${id}/stockids`, { code });
export const removeStockId           = (id, sid)        => request('DELETE', `/stock/entries/${id}/stockids/${sid}`);

// ── EAN Info lookup ─────────────────────────────────────────────────────────
export const getEanInfo = (ean) => request('GET', `/ean-info/${encodeURIComponent(ean)}`);

// ── App Settings ────────────────────────────────────────────────────────────
export const getSettings    = ()           => request('GET', '/settings');
export const getSetting     = (key)        => request('GET', `/settings/${key}`);
export const putSetting     = (key, value) => request('PUT', `/settings/${key}`, { value });

// ── Categories ──────────────────────────────────────────────────────────────
export const getCategories    = ()         => request('GET', '/categories');
export const createCategory   = (data)     => request('POST', '/categories', data);
export const updateCategory   = (id, data) => request('PUT', `/categories/${id}`, data);
export const deleteCategory   = (id)       => request('DELETE', `/categories/${id}`);

// ── Product unit conversions ────────────────────────────────────────────────
export const getProductUnitConversions    = (id)          => request('GET',    `/products/${id}/unit-conversions`);
export const addProductUnitConversion     = (id, data)    => request('POST',   `/products/${id}/unit-conversions`, data);
export const deleteProductUnitConversion  = (id, convId)  => request('DELETE', `/products/${id}/unit-conversions/${convId}`);

// ── Units ───────────────────────────────────────────────────────────────────
export const getUnits    = ()         => request('GET', '/units');
export const createUnit  = (data)     => request('POST', '/units', data);
export const updateUnit  = (id, data) => request('PUT', `/units/${id}`, data);
export const deleteUnit  = (id)       => request('DELETE', `/units/${id}`);
export const addConversion    = (id, data)       => request('POST', `/units/${id}/conversions`, data);
export const deleteConversion = (id, convId)     => request('DELETE', `/units/${id}/conversions/${convId}`);

// ── Stock ───────────────────────────────────────────────────────────────────
export const getStockEntries  = (params = {}) => {
  const q = new URLSearchParams(params).toString();
  return request('GET', `/stock/entries${q ? '?' + q : ''}`);
};
export const createStockEntry = (data)     => request('POST', '/stock/entries', data);
export const updateStockEntry = (id, data) => request('PUT', `/stock/entries/${id}`, data);
export const deleteStockEntry = (id)       => request('DELETE', `/stock/entries/${id}`);
export const getStockSummary            = ()     => request('GET', '/stock/summary');
export const getStockEntryByStockId     = (code) => request('GET', `/stock/entries/by-stockid/${encodeURIComponent(code)}`);
export const getCategoryStockSummary = ()  => request('GET', '/stock/category-summary');
