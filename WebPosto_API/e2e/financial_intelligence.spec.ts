import { test, expect } from "@playwright/test";
import {
  gotoFinanceCenter,
  selectFilialByCode,
  waitForFinanceCenterLoaded,
  FC_PERIOD,
} from "./helpers/financeCenter.helpers";

test.describe("Financial Intelligence F01.3", () => {
  test("bloco inteligência visível após snapshot", async ({ page }) => {
    await gotoFinanceCenter(page);
    await waitForFinanceCenterLoaded(page);
    await page.waitForSelector('[data-testid="fc-intelligence"]', { timeout: 120000 });
    await expect(page.locator('[data-testid="fc-intelligence"]')).toBeVisible();
  });

  test("filtro 11495 mantém inteligência", async ({ page }) => {
    await gotoFinanceCenter(page);
    await selectFilialByCode(page, "11495");
    await page.waitForURL(/empresaCodigo=11495/);
    await page.waitForSelector('[data-testid="fc-intelligence"]', { timeout: 120000 });
  });

  test("widgets F01.4-C fornecedor visíveis", async ({ page }) => {
    await gotoFinanceCenter(page);
    await waitForFinanceCenterLoaded(page);
    await page.waitForSelector('[data-testid="fc-supplier-cards"]', { timeout: 120000 });
    await expect(page.locator('[data-testid="fc-supplier-cards"]')).toBeVisible();
  });
});
