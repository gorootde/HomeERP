const BASE = '/api';

async function req(method, path, body, isFormData = false) {
  const opts = { method, headers: {} };
  if (body !== undefined && !isFormData) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  } else if (isFormData) {
    opts.body = body;
  }
  const res = await fetch(BASE + path, opts);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

const get = (path) => req('GET', path);
const post = (path, body) => req('POST', path, body);
const put = (path, body) => req('PUT', path, body);
const del = (path) => req('DELETE', path);
const postForm = (path, fd) => req('POST', path, fd, true);

// Products
export const getProducts = (search = '', limit = 500) =>
  get(`/products?search=${encodeURIComponent(search)}&limit=${limit}`);
export const getProduct = (id) => get(`/products/${id}`);
export const createProduct = (data) => post('/products', data);
export const updateProduct = (id, data) => put(`/products/${id}`, data);
export const deleteProduct = (id) => del(`/products/${id}`);
export const addEan = (id, code) => post(`/products/${id}/ean`, { code });
export const removeEan = (id, eanId) => del(`/products/${id}/ean/${eanId}`);
export const getByEan = (ean) => get(`/products/by-ean/${ean}`);
export const setImageFromUrl = (id, url) => post(`/products/${id}/image-from-url`, { url });
export const uploadProductImage = (id, formData) => postForm(`/products/${id}/image`, formData);
export const deleteProductImage = (id) => del(`/products/${id}/image`);
export const getProductUnitConversions = (id) => get(`/products/${id}/unit-conversions`);
export const addProductUnitConversion = (id, data) => post(`/products/${id}/unit-conversions`, data);
export const deleteProductUnitConversion = (id, convId) => del(`/products/${id}/unit-conversions/${convId}`);

// Vaults
export const getVaults = () => get('/vaults');
export const createVault = (data) => post('/vaults', data);
export const updateVault = (id, data) => put(`/vaults/${id}`, data);
export const deleteVault = (id) => del(`/vaults/${id}`);

// Tags
export const getTags = () => get('/tags');
export const addTagToProduct = (id, name) => post(`/products/${id}/tags`, { name });
export const removeTagFromProduct = (id, name) => del(`/products/${id}/tags/${encodeURIComponent(name)}`);
export const addTagToVault = (id, name) => post(`/vaults/${id}/tags`, { name });
export const removeTagFromVault = (id, name) => del(`/vaults/${id}/tags/${encodeURIComponent(name)}`);
export const addTagToStockEntry = (id, name) => post(`/stock/entries/${id}/tags`, { name });
export const removeTagFromStockEntry = (id, name) => del(`/stock/entries/${id}/tags/${encodeURIComponent(name)}`);

// Stock Entries
export const getStockEntries = (params = {}) => {
  const q = new URLSearchParams({ limit: 2000, ...params }).toString();
  return get(`/stock/entries?${q}`);
};
export const createStockEntry = (data) => post('/stock/entries', data);
export const updateStockEntry = (id, data) => put(`/stock/entries/${id}`, data);
export const deleteStockEntry = (id) => del(`/stock/entries/${id}`);
export const getStockSummary = () => get('/stock/summary');
export const getCategoryStockSummary = () => get('/stock/category-summary');
export const getStockEntryByStockId = (code) => get(`/stock/entries/by-stockid/${encodeURIComponent(code)}`);

// Stock IDs
export const addStockId = (entryId, code) => post(`/stock/entries/${entryId}/stockids`, { code });
export const removeStockId = (entryId, sid) => del(`/stock/entries/${entryId}/stockids/${sid}`);

// EAN Info
export const getEanInfo = (ean) => get(`/ean-info/${ean}`);

// Settings
export const getSettings = () => get('/settings');
export const getSetting = (key) => get(`/settings/${key}`);
export const putSetting = (key, value) => put(`/settings/${key}`, { value });

// Categories
export const getCategories = () => get('/categories');
export const createCategory = (data) => post('/categories', data);
export const updateCategory = (id, data) => put(`/categories/${id}`, data);
export const deleteCategory = (id) => del(`/categories/${id}`);

// Units
export const getUnits = () => get('/units');
export const createUnit = (data) => post('/units', data);
export const updateUnit = (id, data) => put(`/units/${id}`, data);
export const deleteUnit = (id) => del(`/units/${id}`);
export const addUnitConversion = (id, data) => post(`/units/${id}/conversions`, data);
export const deleteUnitConversion = (id, convId) => del(`/units/${id}/conversions/${convId}`);

// Data Transfer
export const getExportModels = () => get('/export/models');
export const exportData = (tables) => req('POST', '/export', { tables }, false);
export const previewImport = (formData) => postForm('/import/preview', formData);
export const applyImport = (importId) => post(`/import/apply/${importId}`);

// OpenAPI
export const getOpenApiSpec = () => get('/openapi.json');
