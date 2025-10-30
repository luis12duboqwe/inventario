// [PACK24-E2E-ENTITIES-START]
import { test, expect } from '@playwright/test';

test.describe('Ventas entities smoke', () => {
  test('quotes list render', async ({ page }) => {
    await page.route('**/api/quotes**', async route => {
      await route.fulfill({
        json: {
          items: [
            {
              id: 'Q1',
              number: 'Q-1',
              date: '2025-01-01',
              lines: [],
              totals: { sub: 0, disc: 0, tax: 0, grand: 0 },
              status: 'OPEN',
            },
          ],
          total: 1,
          page: 1,
          pageSize: 20,
        },
      });
    });
    await page.goto('/sales/quotes');
    const visible = await page.locator('text=Q-1').first().isVisible().catch(() => false);
    expect(visible).toBeTruthy();
  });

  test('customers list render', async ({ page }) => {
    await page.route('**/api/customers**', async route => {
      await route.fulfill({
        json: {
          items: [
            {
              id: 'C1',
              name: 'Luis Dubon',
              phone: '555-555',
            },
          ],
          total: 1,
          page: 1,
          pageSize: 20,
        },
      });
    });
    await page.goto('/sales/customers');
    const visible = await page.locator('text=Luis Dubon').first().isVisible().catch(() => false);
    expect(visible).toBeTruthy();
  });
});
// [PACK24-E2E-ENTITIES-END]
