// [PACK24-E2E-ROUTING-START]
import { test, expect } from '@playwright/test';

test.describe('Ventas: routing/render', () => {
  test('Dashboard Ventas', async ({ page }) => {
    await page.goto('/sales');
    const heading = page.getByRole('heading', { name: /ventas/i });
    const dashboard = page.locator('[data-testid="sales-dashboard"]').first();

    const headingVisible = await heading
      .waitFor({ state: 'visible', timeout: 3000 })
      .then(() => true)
      .catch(() => false);

    if (!headingVisible) {
      await expect(dashboard).toBeVisible({ timeout: 3000 });
    } else {
      expect(headingVisible).toBeTruthy();
    }
  });

  test('POS', async ({ page }) => {
    await page.goto('/sales/pos');
    const visible = await page
      .locator('[data-testid="pos-page"], text=POS')
      .first()
      .isVisible()
      .catch(() => false);
    expect(visible).toBeTruthy();
  });

  test('Cotizaciones', async ({ page }) => {
    await page.goto('/sales/quotes');
    const visible = await page
      .locator('[data-testid="quotes-list"], text=Cotizaciones')
      .first()
      .isVisible()
      .catch(() => false);
    expect(visible).toBeTruthy();
  });

  test('Devoluciones', async ({ page }) => {
    await page.goto('/sales/returns');
    const visible = await page
      .locator('[data-testid="returns-list"], text=Devoluciones')
      .first()
      .isVisible()
      .catch(() => false);
    expect(visible).toBeTruthy();
  });

  test('Clientes', async ({ page }) => {
    await page.goto('/sales/customers');
    const visible = await page
      .locator('[data-testid="customers-list"], text=Clientes')
      .first()
      .isVisible()
      .catch(() => false);
    expect(visible).toBeTruthy();
  });

  test('Cierre de caja', async ({ page }) => {
    await page.goto('/sales/cash-close');
    const visible = await page
      .locator('[data-testid="cash-close"], text=Cierre de caja')
      .first()
      .isVisible()
      .catch(() => false);
    expect(visible).toBeTruthy();
  });
});
// [PACK24-E2E-ROUTING-END]
