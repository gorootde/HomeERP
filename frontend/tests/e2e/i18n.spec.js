import { test, expect } from '@playwright/test';

// The language store is persisted to localStorage and applied on load, so the
// observable contract is "pick a language → it sticks across navigations".
// German is the default, so these specs start from a clean context and drive
// the switch through the UI – no useLanguage() seeding (its addInitScript would
// re-force the language on every reload and mask the behaviour under test).

test('switching to English relabels the UI after navigation', async ({ page }) => {
  await page.goto('/settings');
  await expect(page.getByRole('heading', { name: 'Einstellungen' })).toBeVisible();

  await page.getByRole('button', { name: 'English' }).click();
  await page.goto('/dashboard');

  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  const nav = page.locator('nav').first();
  await expect(nav.getByRole('link', { name: 'Products' })).toBeVisible();
  await expect(nav.getByRole('link', { name: 'Stock' })).toBeVisible();
});

test('the chosen language survives a reload', async ({ page }) => {
  await page.goto('/settings');
  await page.getByRole('button', { name: 'English' }).click();
  await page.reload();

  await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();

  // switch back so later specs see the German default
  await page.getByRole('button', { name: 'Deutsch' }).click();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Einstellungen' })).toBeVisible();
});
