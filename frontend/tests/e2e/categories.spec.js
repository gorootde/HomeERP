import { test, expect } from '@playwright/test';
import { makeApi, uid, uabbr, useLanguage } from './helpers.js';

test.beforeEach(async ({ page }) => {
  await useLanguage(page, 'de');
  await page.goto('/settings/categories');
  await expect(page.getByRole('heading', { name: 'Kategorien' })).toBeVisible();
});

test('create a category with a minimum stock level', async ({ page }) => {
  const api = await makeApi();
  try {
    const unit = await api.createUnit(uid('Litre'), uabbr('l'));
    await page.reload();

    const name = uid('Beverages');
    await page.getByRole('button', { name: 'Kategorie hinzufügen' }).click();
    const dialog = page.getByRole('dialog', { name: 'Neue Kategorie' });
    await dialog.getByPlaceholder('z.B. Getränke').fill(name);
    await dialog.getByPlaceholder('0').fill('12');
    await dialog.getByRole('combobox').selectOption({ label: `${unit.name} (${unit.abbreviation})` });
    await dialog.getByRole('button', { name: 'Erstellen' }).click();

    await expect(page.getByText('Kategorie erstellt')).toBeVisible();
    const row = page.getByRole('row', { name: new RegExp(name) });
    await expect(row).toContainText('12');
  } finally {
    await api.dispose();
  }
});

test('edit and delete a category', async ({ page }) => {
  const api = await makeApi();
  try {
    const name = uid('EditCat');
    await api.createCategory(name);
    await page.reload();

    await page.getByRole('row', { name: new RegExp(name) }).getByRole('button', { name: 'Bearbeiten' }).click();
    const renamed = uid('RenamedCat');
    const dialog = page.getByRole('dialog', { name: 'Kategorie bearbeiten' });
    await dialog.getByPlaceholder('z.B. Getränke').fill(renamed);
    await dialog.getByRole('button', { name: 'Speichern' }).click();
    await expect(page.getByText('Kategorie gespeichert')).toBeVisible();

    await page.getByRole('row', { name: new RegExp(renamed) }).getByRole('button').last().click();
    await page.getByRole('alertdialog').getByRole('button', { name: 'Löschen' }).click();
    await expect(page.getByText('Kategorie gelöscht')).toBeVisible();
    await expect(page.getByRole('row', { name: new RegExp(renamed) })).toHaveCount(0);
  } finally {
    await api.dispose();
  }
});
