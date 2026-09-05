import { request as pwRequest } from '@playwright/test';

export const BACKEND = 'http://127.0.0.1:8000';

/** Unique suffix so parallel-safe, retry-safe entity names never collide. */
export function uid(prefix = 'e2e') {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
}

/**
 * Unique unit abbreviation. `units.abbreviation` is UNIQUE and capped at 16
 * chars, so `uid(...).slice(0, N)` is not safe – its leading chars barely
 * change between runs and collide. Keep the random tail instead.
 */
export function uabbr(prefix = 'u') {
  return `${prefix}${Math.random().toString(36).slice(2, 10)}${Date.now().toString(36).slice(-4)}`.slice(0, 16);
}

/**
 * Thin REST client for arranging backend state directly (fast + reliable),
 * leaving the UI assertions to the specs themselves.
 */
export async function makeApi() {
  const ctx = await pwRequest.newContext({ baseURL: BACKEND });

  const unwrap = async (res, expected = [200, 201]) => {
    if (!expected.includes(res.status())) {
      throw new Error(`${res.url()} → ${res.status()}: ${await res.text()}`);
    }
    return res.status() === 204 ? null : res.json();
  };

  return {
    ctx,
    dispose: () => ctx.dispose(),

    createUnit: (name = uid('Unit'), abbreviation = uabbr('u')) =>
      ctx.post('/api/units', { data: { name, abbreviation } }).then((r) => unwrap(r)),

    createCategory: (data) =>
      ctx
        .post('/api/categories', { data: typeof data === 'string' ? { name: data } : data })
        .then((r) => unwrap(r)),

    createVault: (description = uid('Vault')) =>
      ctx.post('/api/vaults', { data: { description } }).then((r) => unwrap(r)),

    createProduct: (data = {}) =>
      ctx
        .post('/api/products', {
          data: {
            vendor: data.vendor ?? uid('Vendor'),
            name: data.name ?? uid('Product'),
            ean_codes: data.ean_codes ?? [],
            ...data,
          },
        })
        .then((r) => unwrap(r)),

    updateProduct: (id, data) =>
      ctx.put(`/api/products/${id}`, { data }).then((r) => unwrap(r)),

    createProductUnitConversion: (productId, data) =>
      ctx.post(`/api/products/${productId}/unit-conversions`, { data }).then((r) => unwrap(r)),

    createStockEntry: (data) => ctx.post('/api/stock/entries', { data }).then((r) => unwrap(r)),

    getStockEntry: (id) => ctx.get(`/api/stock/entries/${id}`).then((r) => unwrap(r)),

    putSetting: (key, value) =>
      ctx.put(`/api/settings/${key}`, { data: { value } }).then((r) => unwrap(r)),
    getSetting: (key) => ctx.get(`/api/settings/${key}`).then((r) => unwrap(r)),

    listProducts: () => ctx.get('/api/products?limit=500').then((r) => unwrap(r)),
    listStockEntries: () => ctx.get('/api/stock/entries?limit=2000').then((r) => unwrap(r)),
  };
}

/** Force the UI language so text assertions are deterministic. */
export async function useLanguage(page, lang = 'de') {
  await page.addInitScript((l) => {
    try {
      window.localStorage.setItem('lang', l);
    } catch {}
  }, lang);
}
