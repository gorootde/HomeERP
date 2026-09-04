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
    await dialog.getByRole('combobox').first().selectOption(String(product.id));
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
