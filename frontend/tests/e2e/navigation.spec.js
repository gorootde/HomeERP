import { test, expect } from '@playwright/test';
import { useLanguage } from './helpers.js';

test.beforeEach(async ({ page }) => {
  await useLanguage(page, 'de');
});

test('root redirects to the dashboard', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
});

test('sidebar links reach every primary section', async ({ page }) => {
  await page.goto('/dashboard');

  const nav = page.locator('nav').first();
  for (const [label, path, heading] of [
    ['Produkte', '/products', 'Produkte'],
    ['Lager', '/stock', 'Lagerbestand'],
    ['Scanner', '/scanner', 'Scanner'],
    ['Inventur', '/inventory', 'Inventur'],
    ['Einstellungen', '/settings', 'Einstellungen'],
  ]) {
    await nav.getByRole('link', { name: label, exact: true }).click();
    await expect(page).toHaveURL(new RegExp(`${path}$`));
    await expect(page.getByRole('heading', { name: heading }).first()).toBeVisible();
  }
});

test('the API docs route renders', async ({ page }) => {
  await page.goto('/apidocs');
  await expect(page).toHaveURL(/\/apidocs$/);
});

test('the app shell shows the HomeERP brand', async ({ page }) => {
  await page.goto('/dashboard');
  await expect(page.locator('nav').first().getByText('HomeERP')).toBeVisible();
});
