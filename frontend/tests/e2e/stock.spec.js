import { test, expect } from '@playwright/test';
import { makeApi, uid, uabbr, useLanguage } from './helpers.js';

async function seedProductAndVault(api) {
  const unit = await api.createUnit(uid('Piece'), uabbr('pc'));
  const product = await api.createProduct({ name: uid('StockProduct'), unit_id: unit.id });
  const vault = await api.createVault(uid('StockVault'));
  return { product, vault };
}

test.beforeEach(async ({ page }) => {
  await useLanguage(page, 'de');
});

test('add a stock entry through the modal', async ({ page }) => {
  const api = await makeApi();
  try {
    const { product, vault } = await seedProductAndVault(api);
    await page.goto('/stock');
    await expect(page.getByRole('heading', { name: 'Lagerbestand' })).toBeVisible();

    await page.getByRole('button', { name: 'Eintrag hinzufügen' }).click();
    const dialog = page.getByRole('dialog', { name: 'Neuer Eintrag' });
    await dialog.getByRole('combobox').first().fill(product.name);
    await dialog.getByRole('option', { name: new RegExp(product.name) }).click();
    await dialog.getByRole('combobox').nth(1).selectOption({ label: vault.description });
    await dialog.getByRole('spinbutton').first().fill('4');
    await dialog.getByRole('button', { name: 'Erstellen' }).click();

    await expect(page.getByText('Eintrag hinzugefügt')).toBeVisible();
    const row = page.getByRole('row', { name: new RegExp(product.name) });
    await expect(row).toBeVisible();
    await expect(row).toContainText('4');
  } finally {
    await api.dispose();
  }
});

test('search products by name, vendor and EAN in the add-entry modal', async ({ page }) => {
  const api = await makeApi();
  try {
    const unit = await api.createUnit(uid('Piece'), uabbr('pc'));
    const vault = await api.createVault(uid('SearchVault'));
    const alpha = await api.createProduct({
      name: uid('Alpha'), vendor: uid('Acme'), unit_id: unit.id, ean_codes: ['4011200296908'],
    });
    const beta = await api.createProduct({
      name: uid('Beta'), vendor: uid('Globex'), unit_id: unit.id, ean_codes: ['9002490100070'],
    });

    await page.goto('/stock');
    await page.getByRole('button', { name: 'Eintrag hinzufügen' }).click();
    const dialog = page.getByRole('dialog', { name: 'Neuer Eintrag' });
    const combo = dialog.getByRole('combobox').first();

    // by vendor
    await combo.fill(beta.vendor);
    await expect(dialog.getByRole('option', { name: new RegExp(beta.name) })).toBeVisible();
    await expect(dialog.getByRole('option', { name: new RegExp(alpha.name) })).toHaveCount(0);

    // by partial EAN
    await combo.fill('40112002');
    await expect(dialog.getByRole('option', { name: new RegExp(alpha.name) })).toBeVisible();
    await expect(dialog.getByRole('option', { name: new RegExp(beta.name) })).toHaveCount(0);

    // pick the EAN match and create the entry
    await dialog.getByRole('option', { name: new RegExp(alpha.name) }).click();
    await dialog.getByRole('combobox').nth(1).selectOption({ label: vault.description });
    await dialog.getByRole('spinbutton').first().fill('2');
    await dialog.getByRole('button', { name: 'Erstellen' }).click();

    await expect(page.getByText('Eintrag hinzugefügt')).toBeVisible();
    await expect(page.getByRole('row', { name: new RegExp(alpha.name) })).toBeVisible();
  } finally {
    await api.dispose();
  }
});

test('filter entries by vault', async ({ page }) => {
  const api = await makeApi();
  try {
    const unit = await api.createUnit(uid('Piece'), uabbr('pc'));
    const p = await api.createProduct({ name: uid('FilterProduct'), unit_id: unit.id });
    const v1 = await api.createVault(uid('Keep'));
    const v2 = await api.createVault(uid('Hide'));
    await api.createStockEntry({ product_id: p.id, vault_id: v1.id, quantity: 1 });
    await api.createStockEntry({ product_id: p.id, vault_id: v2.id, quantity: 2 });

    await page.goto('/stock');
    await expect(page.getByRole('row', { name: new RegExp(p.name) })).toHaveCount(2);

    await page.getByRole('combobox').first().selectOption({ label: v1.description });
    await expect(page.getByRole('row', { name: new RegExp(p.name) })).toHaveCount(1);
  } finally {
    await api.dispose();
  }
});

test('filter entries by category', async ({ page }) => {
  const api = await makeApi();
  try {
    const unit = await api.createUnit(uid('Piece'), uabbr('pc'));
    const cat = await api.createCategory(uid('CatFilter'));
    const vault = await api.createVault(uid('CatVault'));
    const inCat = await api.createProduct({ name: uid('InCatProduct'), unit_id: unit.id, category_id: cat.id });
    const noCat = await api.createProduct({ name: uid('NoCatProduct'), unit_id: unit.id });
    await api.createStockEntry({ product_id: inCat.id, vault_id: vault.id, quantity: 1 });
    await api.createStockEntry({ product_id: noCat.id, vault_id: vault.id, quantity: 2 });

    await page.goto('/stock');
    await expect(page.getByRole('row', { name: new RegExp(inCat.name) })).toBeVisible();
    await expect(page.getByRole('row', { name: new RegExp(noCat.name) })).toBeVisible();

    // category filter is the second select in the filter bar (after vault)
    await page.getByRole('combobox').nth(1).selectOption({ label: cat.name });
    await expect(page.getByRole('row', { name: new RegExp(inCat.name) })).toBeVisible();
    await expect(page.getByRole('row', { name: new RegExp(noCat.name) })).toHaveCount(0);
  } finally {
    await api.dispose();
  }
});

test('edit a stock entry quantity', async ({ page }) => {
  const api = await makeApi();
  try {
    const { product, vault } = await seedProductAndVault(api);
    await api.createStockEntry({ product_id: product.id, vault_id: vault.id, quantity: 3 });
    await page.goto('/stock');

    const row = page.getByRole('row', { name: new RegExp(product.name) });
    await row.getByRole('button', { name: 'Bearbeiten' }).click();
    const dialog = page.getByRole('dialog', { name: 'Eintrag bearbeiten' });
    await dialog.getByRole('spinbutton').first().fill('9');
    await dialog.getByRole('button', { name: 'Speichern' }).click();

    await expect(page.getByText('Eintrag gespeichert')).toBeVisible();
    await expect(page.getByRole('row', { name: new RegExp(product.name) })).toContainText('9');
  } finally {
    await api.dispose();
  }
});

test('editing only the entry unit re-converts the base quantity', async ({ page }) => {
  const api = await makeApi();
  try {
    const gram = await api.createUnit(uid('Gramm'), uabbr('g'));
    const product = await api.createProduct({ name: uid('CanProduct'), unit_id: gram.id });
    // 1 Dose = 500 g
    await api.createProductUnitConversion(product.id, {
      unit_name: 'Dose', base_unit_id: gram.id, factor: 500,
    });
    const vault = await api.createVault(uid('StockVault'));
    // an entry mistakenly recorded as "1 g" that is really 1 can
    const entry = await api.createStockEntry({
      product_id: product.id, vault_id: vault.id, quantity: 1,
      entry_unit_key: 'base', entry_quantity: 1,
    });
    await page.goto('/stock');

    const row = page.getByRole('row', { name: new RegExp(product.name) });
    await row.getByRole('button', { name: 'Bearbeiten' }).click();
    const dialog = page.getByRole('dialog', { name: 'Eintrag bearbeiten' });
    // change nothing but the unit
    await dialog.getByRole('combobox').last().selectOption({ label: 'Dose' });
    await dialog.getByRole('button', { name: 'Speichern' }).click();

    await expect(page.getByText('Eintrag gespeichert')).toBeVisible();
    await expect(page.getByRole('row', { name: new RegExp(product.name) }))
      .toContainText('1 Dose (500');

    const saved = await api.getStockEntry(entry.id);
    expect(saved.quantity).toBe(500);
    expect(saved.entry_quantity).toBe(1);
  } finally {
    await api.dispose();
  }
});

test('editing an unrelated field keeps the entry-unit quantity intact', async ({ page }) => {
  const api = await makeApi();
  try {
    const gram = await api.createUnit(uid('Gramm'), uabbr('g'));
    const product = await api.createProduct({ name: uid('CanProduct'), unit_id: gram.id });
    const conv = await api.createProductUnitConversion(product.id, {
      unit_name: 'Dose', base_unit_id: gram.id, factor: 500,
    });
    // product defaults new entries to the "Dose" unit
    await api.updateProduct(product.id, { entry_unit_key: `puc_${conv.id}` });
    const vault = await api.createVault(uid('StockVault'));
    // a correct entry: 1 Dose == 500 g
    const entry = await api.createStockEntry({
      product_id: product.id, vault_id: vault.id, quantity: 500,
      entry_unit_key: `puc_${conv.id}`, entry_quantity: 1,
    });
    await page.goto('/stock');

    const row = page.getByRole('row', { name: new RegExp(product.name) });
    await row.getByRole('button', { name: 'Bearbeiten' }).click();
    const dialog = page.getByRole('dialog', { name: 'Eintrag bearbeiten' });
    await dialog.getByPlaceholder('Kommentar').fill('nur ein Kommentar');
    await dialog.getByRole('button', { name: 'Speichern' }).click();

    await expect(page.getByText('Eintrag gespeichert')).toBeVisible();

    const saved = await api.getStockEntry(entry.id);
    expect(saved.quantity).toBe(500);
    expect(saved.entry_quantity).toBe(1);
  } finally {
    await api.dispose();
  }
});

test('manage stock IDs on an entry', async ({ page }) => {
  const api = await makeApi();
  try {
    const { product, vault } = await seedProductAndVault(api);
    await api.createStockEntry({ product_id: product.id, vault_id: vault.id, quantity: 1 });
    await page.goto('/stock');

    await page.getByRole('row', { name: new RegExp(product.name) }).getByRole('button', { name: 'Stock IDs' }).click();
    const dialog = page.getByRole('dialog', { name: 'Stock IDs verwalten' });
    await dialog.getByPlaceholder('Stock ID').fill('INV-4242');
    await dialog.getByRole('button', { name: 'Hinzufügen' }).click();
    await expect(page.getByText('Stock ID hinzugefügt')).toBeVisible();
    await expect(dialog.getByText('INV-4242')).toBeVisible();

    await dialog.getByText('INV-4242').getByRole('button').click();
    await expect(page.getByText('Stock ID entfernt')).toBeVisible();
  } finally {
    await api.dispose();
  }
});

test('delete a stock entry', async ({ page }) => {
  const api = await makeApi();
  try {
    const { product, vault } = await seedProductAndVault(api);
    await api.createStockEntry({ product_id: product.id, vault_id: vault.id, quantity: 1 });
    await page.goto('/stock');

    await page.getByRole('row', { name: new RegExp(product.name) }).getByRole('button', { name: 'Löschen' }).click();
    await page.getByRole('alertdialog').getByRole('button', { name: 'Löschen' }).click();
    await expect(page.getByText('Eintrag gelöscht')).toBeVisible();
    await expect(page.getByRole('row', { name: new RegExp(product.name) })).toHaveCount(0);
  } finally {
    await api.dispose();
  }
});
