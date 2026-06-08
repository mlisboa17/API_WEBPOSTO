import { test, expect } from "@playwright/test";
import {
  gotoFinanceCenter,
  waitForFinanceCenterLoaded,
} from "./helpers/financeCenter.helpers";

test.describe("Financial Health Score F01.3", () => {
  test("health score card na inteligência", async ({ page }) => {
    await gotoFinanceCenter(page);
    await waitForFinanceCenterLoaded(page);
    await page.waitForSelector('[data-testid="fc-intelligence"]', { timeout: 120000 });
    await expect(page.locator('[data-testid="fc-intelligence"] .fc-card').first()).toContainText(/Score|—/);
  });
});
