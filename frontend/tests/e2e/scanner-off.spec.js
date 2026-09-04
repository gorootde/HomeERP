import { test, expect } from '@playwright/test';
import { makeApi, useLanguage } from './helpers.js';

// A fresh, purely-numeric EAN (isStockId() treats non-digit-only codes as a
// stock id) that doesn't exist in the DB yet, so the scan falls through to
// the "unknown EAN -> ask OpenFoodFacts" branch.
const EAN = `40${Date.now()}`.slice(0, 13);

test.beforeEach(async ({ page }) => {
  await useLanguage(page, 'de');
  // Arm the scanner's test-only scan hook (window.__scanCode) — the fake
  // camera device can't produce a decodable barcode image, so this is how
  // the test drives the same handleScan() a real scan would call.
  await page.addInitScript(() => { window.__E2E_TEST_HOOKS__ = true; });
});

test('OpenFoodFacts data prefills the new-product dialog, including the matched unit', async ({ page }) => {
  const api = await makeApi();
  // Reuse a pre-existing "g" unit if this (locally reused, non-CI) e2e DB
  // already has one from an earlier run — units.abbreviation is UNIQUE, and
  // the match under test needs the exact abbreviation "g".
  const existingUnits = await api.ctx.get('/api/units').then((r) => r.json());
  const unit =
    existingUnits.find((u) => u.abbreviation.toLowerCase() === 'g') ||
    (await api.createUnit('Gramm', 'g'));
  await api.dispose();

  await page.route('**/api/ean-info/**', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        name: 'Bio Cola',
        vendor: 'Fritz',
        size: '200 g',
        image_url: null,
        source: 'openfoodfacts',
      }),
    }),
  );

  await page.goto('/scanner');
  // Wait for onMount's data load (vaults/products/units/...) to finish and
  // install the hook, rather than for the scan button — that one renders
  // from local state alone and doesn't prove the async setup has landed.
  await page.waitForFunction(() => typeof window.__scanCode === 'function');

  await page.evaluate((code) => window.__scanCode(code), EAN);

  await expect(page.getByText('Unbekannte EAN')).toBeVisible();
  await expect(page.getByText('OpenFoodFacts: Bio Cola')).toBeVisible();

  await page.getByRole('button', { name: 'Neues Produkt' }).click();

  const dialog = page.getByRole('dialog', { name: 'Neues Produkt erstellen' });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByPlaceholder('Produktname')).toHaveValue('Bio Cola');
  await expect(dialog.getByPlaceholder('Hersteller')).toHaveValue('Fritz');

  const unitSelect = dialog.locator(
    'xpath=.//label[normalize-space(text())="Einheit"]/following-sibling::select[1]',
  );
  await expect(unitSelect).toHaveValue(String(unit.id));

  // The "200 g" OFF size is staged as a "Stück" packaging conversion (1 Stück = 200 g)
  // rather than a bare size field — that's how this app now models package sizes.
  // "Stück" also shows up again as a selectable target unit further down (for
  // adding another conversion), so scope to the first (existing-row) match.
  await expect(dialog.getByText('Stück', { exact: true }).first()).toBeVisible();
  await expect(dialog.getByText('200 × g')).toBeVisible();

  await dialog.getByRole('button', { name: 'Produkt erstellen' }).click();
  // createNewProduct() awaits several sequential requests (create product,
  // stage the puc conversion, refresh) before this toast fires — wait for it
  // instead of racing the backend with the verification request below.
  await expect(page.getByText('Produkt erstellt')).toBeVisible();

  const api2 = await makeApi();
  try {
    const products = await api2.listProducts();
    const created = products.find((p) => p.ean_codes?.some((e) => e.code === EAN));
    expect(created).toBeTruthy();
    expect(created.unit_id).toBe(unit.id);
  } finally {
    await api2.dispose();
  }
});
