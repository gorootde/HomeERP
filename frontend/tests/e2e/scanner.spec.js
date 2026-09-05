import { test, expect } from '@playwright/test';
import { useLanguage, makeApi, uid } from './helpers.js';

test.beforeEach(async ({ page }) => {
  await useLanguage(page, 'de');
});

/**
 * Seed a product with an EAN, open /scanner, inject the scan via the test hook,
 * and create a stock entry through the "Neuer Eintrag" modal. Returns the seeded
 * product + vault so the caller can assert against them.
 */
async function seedAndScan(page, api, { quantity = 1, comment = null, stockId = null } = {}) {
  const unit = await api.createUnit();
  const vault = await api.createVault(uid('Vault'));
  const ean = String(Date.now() + Math.floor(Math.random() * 1000)).slice(0, 13);
  const product = await api.createProduct({
    name: uid('Prod'),
    vendor: uid('Vendor'),
    unit_id: unit.id,
    ean_codes: [ean],
  });

  await page.addInitScript(() => {
    window.__E2E_TEST_HOOKS__ = true;
  });
  await page.goto('/scanner');
  await page.waitForFunction(() => typeof window.__scanCode === 'function');
  await page.evaluate((c) => window.__scanCode(c), ean);

  await page.getByRole('button', { name: 'Eintrag hinzufügen' }).click();
  const dialog = page.getByRole('dialog', { name: 'Neuer Eintrag' });
  await expect(dialog).toBeVisible();
  await dialog.getByRole('combobox').selectOption({ label: vault.description });
  await dialog.getByRole('spinbutton').fill(String(quantity));
  if (comment) await dialog.getByPlaceholder('Kommentar').fill(comment);
  if (stockId) await dialog.getByPlaceholder('Stock-ID scannen oder eingeben…').fill(stockId);
  await dialog.getByRole('button', { name: 'Erstellen' }).click();
  await expect(dialog).toBeHidden();

  return { product, vault, ean };
}

test('the scanner page mounts the camera view and a stop control', async ({ page }) => {
  await page.goto('/scanner');
  await expect(page.getByRole('heading', { name: 'Scanner' })).toBeVisible();

  // The scanner starts active; with a fake media device it reaches "Aktiv"
  // (or surfaces an error string) – either way the status line renders.
  await expect(page.getByRole('button', { name: 'Scanner stoppen' })).toBeVisible();

  const status = page.locator('p.text-green-600, p.text-red-600, p.text-gray-500');
  await expect(status.first()).toBeVisible({ timeout: 15_000 });
});

test('the scanner can be toggled off and on', async ({ page }) => {
  await page.goto('/scanner');
  await page.getByRole('button', { name: 'Scanner stoppen' }).click();
  const startBtn = page.getByRole('button', { name: 'Scanner starten' });
  await expect(startBtn).toBeVisible();

  await startBtn.click();
  await expect(page.getByRole('button', { name: 'Scanner stoppen' })).toBeVisible();
});

test('the EAN hint card is shown when there is no scan result', async ({ page }) => {
  await page.goto('/scanner');
  await expect(page.getByText('EAN / Barcode')).toBeVisible();
});

test('the last entry can be re-opened and edited after a scan', async ({ page }) => {
  const api = await makeApi();
  try {
    const { product } = await seedAndScan(page, api, { quantity: 2, comment: 'first' });

    const editBtn = page.getByRole('button', { name: 'Letzten Eintrag bearbeiten' });
    await expect(editBtn).toBeVisible();
    await editBtn.click();

    const dialog = page.getByRole('dialog', { name: 'Eintrag bearbeiten' });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText(product.name)).toBeVisible();
    await expect(dialog.getByRole('spinbutton')).toHaveValue('2');
    await expect(dialog.getByPlaceholder('Kommentar')).toHaveValue('first');

    await dialog.getByRole('spinbutton').fill('5');
    await dialog.getByPlaceholder('Kommentar').fill('edited');
    await dialog.getByRole('button', { name: 'Speichern' }).click();
    await expect(dialog).toBeHidden();

    await expect(page.getByText('Eintrag aktualisiert')).toBeVisible();
    await expect(editBtn).toBeVisible();

    const entries = (await api.listStockEntries()).filter((e) => e.product_id === product.id);
    expect(entries).toHaveLength(1);
    expect(entries[0].quantity).toBe(5);
    expect(entries[0].comment).toBe('edited');
  } finally {
    await api.dispose();
  }
});

test('the last entry can be duplicated without copying its stock id', async ({ page }) => {
  const api = await makeApi();
  try {
    await api.putSetting('stock_id_mode', 'manual');
    const { product, vault } = await seedAndScan(page, api, {
      quantity: 3,
      comment: 'orig',
      stockId: 'SID-DUP-1',
    });

    await page.getByRole('button', { name: 'Letzten Eintrag duplizieren' }).click();

    const dialog = page.getByRole('dialog', { name: 'Neuer Eintrag' });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText(product.name)).toBeVisible();
    await expect(dialog.getByRole('combobox')).toHaveValue(String(vault.id));
    await expect(dialog.getByRole('spinbutton')).toHaveValue('3');
    await expect(dialog.getByPlaceholder('Kommentar')).toHaveValue('orig');
    await expect(dialog.getByPlaceholder('Stock-ID scannen oder eingeben…')).toHaveValue('');

    await dialog.getByRole('button', { name: 'Erstellen' }).click();
    await expect(dialog).toBeHidden();

    // Two "Eintrag erstellt" toasts now exist (the seed create + this duplicate) —
    // assert the result via the API instead of the ambiguous toast text.
    await expect
      .poll(async () =>
        (await api.listStockEntries()).filter((e) => e.product_id === product.id).length
      )
      .toBe(2);
    const entries = (await api.listStockEntries()).filter((e) => e.product_id === product.id);
    const codes = entries.flatMap((e) => (e.stock_ids || []).map((s) => s.code));
    expect(codes.filter((c) => c === 'SID-DUP-1')).toHaveLength(1);
    expect(entries.every((e) => e.quantity === 3)).toBe(true);
  } finally {
    await api.dispose();
  }
});

test('the product of the last entry can be edited from the scanner', async ({ page }) => {
  const api = await makeApi();
  try {
    const { product } = await seedAndScan(page, api, { quantity: 1 });

    await page.getByRole('button', { name: 'Letztes Produkt bearbeiten' }).click();
    const dialog = page.getByRole('dialog', { name: 'Produkt bearbeiten' });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByPlaceholder('Produktname')).toHaveValue(product.name);

    const newName = product.name + ' EDITED';
    await dialog.getByPlaceholder('Produktname').fill(newName);
    await dialog.getByRole('button', { name: 'Speichern' }).click();
    await expect(dialog).toBeHidden();
    await expect(page.getByText('Produkt aktualisiert')).toBeVisible();

    const updated = (await api.listProducts()).find((p) => p.id === product.id);
    expect(updated.name).toBe(newName);

    await page.getByRole('button', { name: 'Letzten Eintrag duplizieren' }).click();
    await expect(
      page.getByRole('dialog', { name: 'Neuer Eintrag' }).getByText(newName)
    ).toBeVisible();
  } finally {
    await api.dispose();
  }
});
