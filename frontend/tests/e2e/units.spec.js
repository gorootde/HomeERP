import { test, expect } from '@playwright/test';
import { makeApi, uid, uabbr, useLanguage } from './helpers.js';

test.beforeEach(async ({ page }) => {
  await useLanguage(page, 'de');
  await page.goto('/settings/units');
  await expect(page.getByRole('heading', { name: 'Einheiten' })).toBeVisible();
});

test('create and delete a unit', async ({ page }) => {
  const name = uid('Kilogram');
  const abbr = uabbr('kg');

  await page.getByRole('button', { name: 'Einheit hinzufügen' }).click();
  const dialog = page.getByRole('dialog', { name: 'Neue Einheit' });
  await dialog.getByPlaceholder('z.B. Kilogramm').fill(name);
  await dialog.getByPlaceholder('z.B. kg').fill(abbr);
  await dialog.getByRole('button', { name: 'Erstellen' }).click();
  await expect(page.getByText('Einheit erstellt')).toBeVisible();

  const row = page.getByRole('row', { name: new RegExp(name) });
  await expect(row).toBeVisible();

  await row.getByRole('button').last().click();
  await page.getByRole('alertdialog').getByRole('button', { name: 'Löschen' }).click();
  await expect(page.getByText('Einheit gelöscht')).toBeVisible();
});

test('add and remove a conversion between two units', async ({ page }) => {
  const api = await makeApi();
  try {
    const litre = await api.createUnit(uid('Litre'), uabbr('l'));
    const ml = await api.createUnit(uid('Millilitre'), uabbr('ml'));
    await page.reload();

    await page
      .getByRole('row', { name: new RegExp(litre.name) })
      .getByRole('button', { name: 'Bearbeiten' })
      .click();

    const dialog = page.getByRole('dialog', { name: 'Einheit bearbeiten' });
    await dialog.getByRole('combobox').selectOption({ label: `${ml.name} (${ml.abbreviation})` });
    await dialog.getByPlaceholder('Faktor').fill('1000');
    await dialog.getByRole('button', { name: 'Hinzufügen' }).click();

    await expect(page.getByText('Konvertierung gespeichert')).toBeVisible();
    await expect(dialog.getByText(new RegExp(`1000`))).toBeVisible();
  } finally {
    await api.dispose();
  }
});
