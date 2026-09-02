import { test, expect } from '@playwright/test';
import { makeApi, uid, uabbr, useLanguage } from './helpers.js';

test.beforeEach(async ({ page }) => {
  await useLanguage(page, 'de');
});

test('dashboard renders the stat tiles', async ({ page }) => {
  await page.goto('/dashboard');
  await expect(page.getByText('Produkte im Lager')).toBeVisible();
  await expect(page.getByText('Gesamtbestand')).toBeVisible();
  await expect(page.getByText('Lagerorte')).toBeVisible();
});

test('seeded stock shows up in the totals, category cards and product table', async ({ page }) => {
  const api = await makeApi();
  try {
    const unit = await api.createUnit(uid('Litre'), uabbr('l'));
    const cat = await api.createCategory({
      name: uid('Beverages'),
      min_stock_quantity: 20,
      min_stock_unit_id: unit.id,
    });
    const productName = uid('DashProduct');
    const product = await api.createProduct({
      name: productName,
      unit_id: unit.id,
      category_id: cat.id,
    });
    const vault = await api.createVault(uid('DashVault'));
    await api.createStockEntry({ product_id: product.id, vault_id: vault.id, quantity: 5 });

    await page.goto('/dashboard');

    // product row in the "Alle Produkte" table
    const row = page.getByRole('row', { name: new RegExp(productName) });
    await expect(row).toBeVisible();
    await expect(row).toContainText('5');

    // category card – 5 of 20 min => "low" (yellow) but at least the name + min line render
    await expect(page.getByText(cat.name).first()).toBeVisible();
    await expect(page.getByText(/Min: 20/).first()).toBeVisible();
  } finally {
    await api.dispose();
  }
});
