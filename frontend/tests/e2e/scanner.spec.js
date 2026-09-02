import { test, expect } from '@playwright/test';
import { useLanguage } from './helpers.js';

test.beforeEach(async ({ page }) => {
  await useLanguage(page, 'de');
});

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
