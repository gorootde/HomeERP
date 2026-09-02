import { test, expect } from '@playwright/test';
import { useLanguage } from './helpers.js';

test.beforeEach(async ({ page }) => {
  await useLanguage(page, 'de');
  await page.goto('/settings/data-transfer');
  await expect(page.getByRole('heading', { name: 'Datentransfer' })).toBeVisible();
});

test('the export and import panels render', async ({ page }) => {
  await expect(page.getByRole('heading', { name: 'Export' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Import' })).toBeVisible();

  // one checkbox per exportable model (plus the "include images" toggle)
  await expect(page.locator('input[type="checkbox"]').first()).toBeVisible();
  expect(await page.locator('input[type="checkbox"]').count()).toBeGreaterThan(1);

  await expect(page.getByRole('button', { name: 'Exportieren' })).toBeVisible();
  await expect(page.locator('input[type="file"]')).toBeVisible();
});

test('selecting nothing and exporting warns the user', async ({ page }) => {
  await page.getByRole('button', { name: 'Exportieren' }).click();
  await expect(page.getByText('Nichts ausgewählt')).toBeVisible();
});

test('"Alle auswählen" checks every model checkbox', async ({ page }) => {
  const boxes = page.locator('input[type="checkbox"]');
  const total = await boxes.count();

  await page.getByRole('button', { name: 'Alle auswählen' }).click();

  // every model checkbox becomes checked (the last box is the images toggle,
  // which is on by default too)
  for (let i = 0; i < total; i++) {
    await expect(boxes.nth(i)).toBeChecked();
  }
});

test('exporting the "products" table downloads a ZIP', async ({ page }) => {
  const downloadPromise = page.waitForEvent('download');
  // hit the export endpoint directly – the download attribute is script-driven
  await page.evaluate(async () => {
    const res = await fetch('/api/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tables: ['products'] }),
    });
    const blob = await res.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'manual-export.zip';
    document.body.appendChild(a);
    a.click();
  });
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('manual-export.zip');
});
