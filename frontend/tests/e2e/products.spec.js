import { test, expect } from '@playwright/test';
import { makeApi, uid, useLanguage } from './helpers.js';

test.beforeEach(async ({ page }) => {
  await useLanguage(page, 'de');
  await page.goto('/products');
  await expect(page.getByRole('heading', { name: 'Produkte' })).toBeVisible();
});

test('create a product through the modal', async ({ page }) => {
  const name = uid('UIProduct');
  await page.getByRole('button', { name: 'Produkt hinzufügen' }).click();

  const dialog = page.getByRole('dialog', { name: 'Neues Produkt' });
  await dialog.getByPlaceholder('Produktname').fill(name);
  await dialog.getByPlaceholder('Hersteller').fill('ACME');
  await dialog.getByRole('button', { name: 'Erstellen' }).click();

  await expect(page.getByText('Produkt erstellt')).toBeVisible();
  await expect(page.getByRole('row', { name: new RegExp(name) })).toBeVisible();
});

test('search filters the product list', async ({ page }) => {
  const api = await makeApi();
  try {
    const a = uid('AppleJuice');
    const b = uid('ColaZero');
    await api.createProduct({ name: a, vendor: 'Granini' });
    await api.createProduct({ name: b, vendor: 'Coca' });
    await page.reload();

    await page.getByPlaceholder('Suche nach Name oder Hersteller…').fill(a);
    await expect(page.getByRole('row', { name: new RegExp(a) })).toBeVisible();
    await expect(page.getByRole('row', { name: new RegExp(b) })).toHaveCount(0);
  } finally {
    await api.dispose();
  }
});

test('filter the product list by category', async ({ page }) => {
  const api = await makeApi();
  try {
    const cat = await api.createCategory(uid('Beverages'));
    const inCat = uid('InCat');
    const noCat = uid('NoCat');
    await api.createProduct({ name: inCat, category_id: cat.id });
    await api.createProduct({ name: noCat });
    await page.reload();

    await page.getByRole('combobox').first().selectOption({ label: cat.name });
    await expect(page.getByRole('row', { name: new RegExp(inCat) })).toBeVisible();
    await expect(page.getByRole('row', { name: new RegExp(noCat) })).toHaveCount(0);

    await page.getByRole('combobox').first().selectOption({ label: 'Keine Kategorie' });
    await expect(page.getByRole('row', { name: new RegExp(noCat) })).toBeVisible();
    await expect(page.getByRole('row', { name: new RegExp(inCat) })).toHaveCount(0);
  } finally {
    await api.dispose();
  }
});

test('edit a product name', async ({ page }) => {
  const api = await makeApi();
  try {
    const original = uid('EditMe');
    await api.createProduct({ name: original });
    await page.reload();

    await page
      .getByRole('row', { name: new RegExp(original) })
      .getByRole('button', { name: 'Bearbeiten' })
      .click();

    const dialog = page.getByRole('dialog', { name: 'Produkt bearbeiten' });
    const renamed = uid('Renamed');
    await dialog.getByPlaceholder('Produktname').fill(renamed);
    await dialog.getByRole('button', { name: 'Speichern' }).click();

    await expect(page.getByText('Produkt gespeichert')).toBeVisible();
    await expect(page.getByRole('row', { name: new RegExp(renamed) })).toBeVisible();
  } finally {
    await api.dispose();
  }
});

test('manage EAN codes for a product', async ({ page }) => {
  const api = await makeApi();
  try {
    const name = uid('EanProduct');
    await api.createProduct({ name });
    await page.reload();

    await page
      .getByRole('row', { name: new RegExp(name) })
      .getByRole('button', { name: 'EAN-Codes' })
      .click();

    const dialog = page.getByRole('dialog', { name: 'EAN-Codes verwalten' });
    await dialog.getByPlaceholder('EAN-Code').fill('4001234567890');
    await dialog.getByRole('button', { name: 'Hinzufügen' }).click();

    await expect(page.getByText('EAN hinzugefügt')).toBeVisible();
    await expect(dialog.getByText('4001234567890')).toBeVisible();

    await dialog.getByText('4001234567890').getByRole('button').click();
    await expect(page.getByText('EAN entfernt')).toBeVisible();
  } finally {
    await api.dispose();
  }
});

test('delete a product with confirmation', async ({ page }) => {
  const api = await makeApi();
  try {
    const name = uid('DeleteMe');
    await api.createProduct({ name });
    await page.reload();

    await page
      .getByRole('row', { name: new RegExp(name) })
      .locator('button')
      .last()
      .click();

    const confirm = page.getByRole('alertdialog');
    await expect(confirm.getByText('Produkt wirklich löschen?')).toBeVisible();
    await confirm.getByRole('button', { name: 'Löschen' }).click();

    await expect(page.getByText('Produkt gelöscht')).toBeVisible();
    await expect(page.getByRole('row', { name: new RegExp(name) })).toHaveCount(0);
  } finally {
    await api.dispose();
  }
});
