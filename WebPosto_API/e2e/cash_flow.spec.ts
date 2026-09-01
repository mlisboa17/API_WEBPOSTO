import { test, expect, Page } from "@playwright/test";
import {
  gotoFinanceCenter,
  selectTodosPostos,
  selectFilialByCode,
  waitForFinanceCenterLoaded,
  FC_PERIOD,
} from "./helpers/financeCenter.helpers";

async function gotoCashFlow(page: Page) {
  const params = new URLSearchParams({
    view: "cash-flow",
    dataInicial: FC_PERIOD.dataInicial,
    dataFinal: FC_PERIOD.dataFinal,
  });
  await page.goto(`/app/financial?${params.toString()}`);
  await page.waitForSelector('[data-testid="cash-flow-root"]', { timeout: 90000 });
}

test.describe("Cash Flow F01.2", () => {
  test("render cards e tabela diária", async ({ page }) => {
    await gotoCashFlow(page);
    await expect(page.locator(".cash-flow .fc-card").first()).toBeVisible();
    await expect(page.locator(".cf-table-export tbody tr").first()).toBeVisible();
  });

  test("filtro 11495 altera URL", async ({ page }) => {
    await gotoCashFlow(page);
    await selectFilialByCode(page, "11495");
    await page.waitForURL(/empresaCodigo=11495/);
  });

  test("export CSV", async ({ page }) => {
    await gotoCashFlow(page);
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.locator('[data-testid="cf-export-csv"]').click(),
    ]);
    expect(await download.suggestedFilename()).toContain("fluxo_caixa");
  });
});
