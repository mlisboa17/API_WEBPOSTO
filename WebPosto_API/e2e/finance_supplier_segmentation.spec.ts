import { test, expect } from "@playwright/test";
import {
  gotoFinanceCenter,
  selectFilialByCode,
  waitForFinanceCenterLoaded,
  FC_PERIOD,
} from "./helpers/financeCenter.helpers";

test.describe("Supplier Segmentation F01.4-D", () => {
  test("bloco segmentação visível — todos", async ({ page }) => {
    await gotoFinanceCenter(page);
    await waitForFinanceCenterLoaded(page);
    await page.waitForSelector('[data-testid="fc-segmentation-cards"]', { timeout: 120000 });
    await expect(page.locator('[data-testid="fc-segmentation-cards"]')).toBeVisible();
  });

  test("cenário B — filial 11495", async ({ page }) => {
    await gotoFinanceCenter(page);
    await selectFilialByCode(page, "11495");
    await page.waitForURL(/empresaCodigo=11495/);
    await page.waitForSelector('[data-testid="fc-segmentation-cards"]', { timeout: 120000 });
  });

  test("cenário C — filial 5555", async ({ page }) => {
    await gotoFinanceCenter(page);
    await selectFilialByCode(page, "5555");
    await page.waitForURL(/empresaCodigo=5555/);
    await page.waitForSelector('[data-testid="fc-segmentation-cards"]', { timeout: 120000 });
  });
});
