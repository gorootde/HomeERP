import { test, expect } from '@playwright/test';
import { makeApi, useLanguage } from './helpers.js';

test.beforeEach(async ({ page }) => {
  await useLanguage(page, 'de');
});

test('the label preview image loads and reacts to layout changes', async ({ page }) => {
  await page.goto('/settings/printing');
  await expect(page.getByRole('heading', { name: 'Druck-Einstellungen' })).toBeVisible();

  const preview = page.getByRole('img', { name: 'Label-Vorschau' });
  await expect(preview).toBeVisible();
  // the <img> actually decodes a PNG from the backend
  await expect
    .poll(async () => preview.evaluate((el) => el.naturalWidth))
    .toBeGreaterThan(0);

  const before = await preview.getAttribute('src');
  await page.getByLabel('Layout').selectOption({ label: 'QR groß (Text über QR)' });
  await expect.poll(async () => preview.getAttribute('src')).not.toBe(before);
});

test('test print is disabled until a printer IP is entered, then calls the backend', async ({ page }) => {
  const api = await makeApi();
  await api.putSetting('label_printer_ip', '');
  await api.dispose();

  // stub the actual print so no real network/printer is needed
  await page.route('**/api/settings/printing/test-print', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '{"status":"ok"}' }),
  );

  await page.goto('/settings/printing');
  const testBtn = page.getByRole('button', { name: 'Testdruck' });
  await expect(testBtn).toBeDisabled();

  await page.getByPlaceholder('z.B. 192.168.1.50').fill('192.168.1.50');
  await expect(testBtn).toBeEnabled();
  await testBtn.click();
  await expect(page.getByText('Testdruck gesendet')).toBeVisible();
});

test('saving persists the printer settings on the backend', async ({ page }) => {
  await page.goto('/settings/printing');
  await page.getByPlaceholder('z.B. 192.168.1.50').fill('10.0.0.99');
  await page.getByLabel('Etikettenbreite (Bandbreite)').selectOption('29');
  await page.getByRole('button', { name: 'Speichern' }).click();
  await expect(page.getByText('Einstellungen gespeichert')).toBeVisible();

  const api = await makeApi();
  try {
    expect((await api.getSetting('label_printer_ip')).value).toBe('10.0.0.99');
    expect((await api.getSetting('label_width_mm')).value).toBe('29');
  } finally {
    await api.dispose();
  }
});
