import { test, expect } from '@playwright/test';
import { makeApi, uid, useLanguage } from './helpers.js';

test.beforeEach(async ({ page }) => {
  await useLanguage(page, 'de');
  await page.goto('/settings/vaults');
  await expect(page.getByRole('heading', { name: 'Lagerorte' })).toBeVisible();
});

test('create, edit and delete a vault', async ({ page }) => {
  const name = uid('Cellar');
  await page.getByRole('button', { name: 'Lagerort hinzufügen' }).click();
  let dialog = page.getByRole('dialog', { name: 'Neuer Lagerort' });
  await dialog.getByPlaceholder('z.B. Keller').fill(name);
  await dialog.getByRole('button', { name: 'Erstellen' }).click();
  await expect(page.getByText('Lagerort erstellt')).toBeVisible();

  const row = page.getByRole('row', { name: new RegExp(name) });
  await expect(row).toBeVisible();

  await row.getByRole('button').first().click();
  dialog = page.getByRole('dialog', { name: 'Lagerort bearbeiten' });
  const renamed = uid('Pantry');
  await dialog.getByPlaceholder('z.B. Keller').fill(renamed);
  await dialog.getByRole('button', { name: 'Speichern' }).click();
  await expect(page.getByText('Lagerort gespeichert')).toBeVisible();
  await expect(page.getByRole('row', { name: new RegExp(renamed) })).toBeVisible();

  await page.getByRole('row', { name: new RegExp(renamed) }).getByRole('button').last().click();
  await page.getByRole('alertdialog').getByRole('button', { name: 'Löschen' }).click();
  await expect(page.getByText('Lagerort gelöscht')).toBeVisible();
  await expect(page.getByRole('row', { name: new RegExp(renamed) })).toHaveCount(0);
});

test('add and remove a tag on an existing vault', async ({ page }) => {
  const api = await makeApi();
  try {
    const name = uid('TaggedVault');
    await api.createVault(name);
    await page.reload();

    await page.getByRole('row', { name: new RegExp(name) }).getByRole('button').first().click();
    const dialog = page.getByRole('dialog', { name: 'Lagerort bearbeiten' });
    await dialog.getByPlaceholder('Tag eingeben…').fill('kalt');
    await dialog.getByPlaceholder('Tag eingeben…').press('Enter');
    await expect(dialog.getByText('kalt')).toBeVisible();

    await dialog.getByText('kalt').getByRole('button').click();
    await expect(dialog.getByText('kalt')).toHaveCount(0);
  } finally {
    await api.dispose();
  }
});
