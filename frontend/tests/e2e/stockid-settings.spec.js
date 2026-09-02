import { test, expect } from '@playwright/test';
import { makeApi, useLanguage } from './helpers.js';

test.beforeEach(async ({ page }) => {
  await useLanguage(page, 'de');
});

test.afterEach(async () => {
  // restore defaults so other specs are unaffected
  const api = await makeApi();
  await api.putSetting('stock_id_mode', 'manual');
  await api.dispose();
});

test('switching to "generated" reveals prefix/counter/pad fields and previews the next ID', async ({ page }) => {
  await page.goto('/settings/stockid');
  await expect(page.getByRole('heading', { name: 'Stock ID Konfiguration' })).toBeVisible();

  await page.getByRole('radio', { name: /Automatisch/ }).check();

  await page.getByPlaceholder('z.B. S-').fill('INV-');
  // counter + pad are plain number inputs
  const numbers = page.getByRole('spinbutton');
  await numbers.nth(0).fill('7');
  await numbers.nth(1).fill('5');

  await expect(page.getByText(/Nächste ID:\s*INV-00007/)).toBeVisible();

  await page.getByRole('button', { name: 'Speichern' }).click();
  await expect(page.getByText('Einstellungen gespeichert')).toBeVisible();

  // persisted on the backend
  const api = await makeApi();
  try {
    expect((await api.getSetting('stock_id_mode')).value).toBe('generated');
    expect((await api.getSetting('stock_id_prefix')).value).toBe('INV-');
    expect((await api.getSetting('stock_id_counter')).value).toBe('7');
  } finally {
    await api.dispose();
  }
});

test('the webhook mode shows the URL field and placeholder reference', async ({ page }) => {
  await page.goto('/settings/stockid');
  await page.getByRole('radio', { name: /Extern/ }).check();
  await expect(page.getByText('Platzhalter')).toBeVisible();
  await page.getByPlaceholder('https://…').fill('https://printer.local/next?p={product_id}');
  await page.getByRole('button', { name: 'Speichern' }).click();
  await expect(page.getByText('Einstellungen gespeichert')).toBeVisible();
});
