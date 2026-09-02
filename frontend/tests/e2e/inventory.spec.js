import { test, expect } from '@playwright/test';
import { makeApi, uid, uabbr, useLanguage } from './helpers.js';

test.beforeEach(async ({ page }) => {
  await useLanguage(page, 'de');
});

test('the counting workflow steps from vault selection to an empty result', async ({ page }) => {
  const api = await makeApi();
  try {
    const unit = await api.createUnit(uid('Piece'), uabbr('pc'));
    const product = await api.createProduct({ name: uid('InvProduct'), unit_id: unit.id });
    const vault = await api.createVault(uid('InvVault'));
    await api.createStockEntry({ product_id: product.id, vault_id: vault.id, quantity: 3 });

    await page.goto('/inventory');
    await expect(page.getByRole('heading', { name: 'Inventur' })).toBeVisible();

    // Step 1 – select vault
    await expect(page.getByRole('button', { name: 'Inventur starten' })).toBeDisabled();
    await page.getByRole('combobox').selectOption({ label: vault.description });
    await page.getByRole('button', { name: 'Inventur starten' }).click();

    // Step 2 – counting screen with the three tallies
    await expect(page.getByText('Scans')).toBeVisible();
    await expect(page.getByText('Erwartet')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Scanner starten' })).toBeVisible();

    // Finish with zero scans
    await page.getByRole('button', { name: 'Abschließen' }).click();

    // Step 3 – result: the expected-but-not-scanned product shows as "Fehlend"
    await expect(page.getByRole('heading', { name: 'Ergebnis' })).toBeVisible();
    const row = page.getByRole('row', { name: new RegExp(product.name) });
    await expect(row).toContainText('Fehlend');

    // Restart
    await page.getByRole('button', { name: 'Neue Inventur' }).click();
    await expect(page.getByRole('button', { name: 'Inventur starten' })).toBeVisible();
  } finally {
    await api.dispose();
  }
});

test('cancelling from the counting screen returns to vault selection', async ({ page }) => {
  const api = await makeApi();
  try {
    const vault = await api.createVault(uid('CancelVault'));
    await page.goto('/inventory');
    await page.getByRole('combobox').selectOption({ label: vault.description });
    await page.getByRole('button', { name: 'Inventur starten' }).click();
    await expect(page.getByText('Scans')).toBeVisible();

    await page.getByRole('button', { name: 'Abbrechen' }).click();
    await expect(page.getByRole('button', { name: 'Inventur starten' })).toBeVisible();
  } finally {
    await api.dispose();
  }
});
