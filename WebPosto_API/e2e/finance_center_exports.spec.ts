import { test, expect } from "@playwright/test";
import fs from "fs";
import {
  gotoFinanceCenter,
  waitForFinanceCenterLoaded,
  parseCsvSemicolon,
  scrapeTableTotals,
  selectTodosPostos,
  selectFilialByCode,
  selectFiliaisByCodes,
} from "./helpers/financeCenter.helpers";

async function exportCsvAndRead(page: import("@playwright/test").Page): Promise<string[][]> {
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.locator('[data-testid="fc-export-csv"]').click(),
  ]);
  const path = await download.path();
  expect(path).toBeTruthy();
  const text = fs.readFileSync(path!, "utf-8");
  return parseCsvSemicolon(text);
}

test.describe("Finance Center — paridade exportação", () => {
  test.beforeEach(async ({ page }) => {
    await gotoFinanceCenter(page);
    await waitForFinanceCenterLoaded(page);
  });

  test("CSV contém blocos principais (dados filtrados completos)", async ({ page }) => {
    const rows = await exportCsvAndRead(page);
    const sections = rows.slice(1).map((r) => r[0]);
    expect(sections.some((s) => s.includes("Despesas Gerenciais"))).toBeTruthy();
    expect(sections.some((s) => s.includes("Contas a Pagar"))).toBeTruthy();
    expect(sections.some((s) => s.includes("Tesouraria"))).toBeTruthy();
    expect(sections.some((s) => s.includes("LOGOS"))).toBeTruthy();
    expect(sections.some((s) => s.includes("Caixa"))).toBeTruthy();
  });

  test("Paridade tabela ↔ CSV (aging Contas a Pagar)", async ({ page }) => {
    const rows = page.locator('[data-testid="fc-aging-payables"] tbody tr[data-bucket]');
    const count = await rows.count();
    const csvRows = await exportCsvAndRead(page);
    const csvMap = new Map(csvRows.slice(1).map((r) => [r[0], r]));

    for (let i = 0; i < count; i += 1) {
      const row = rows.nth(i);
      const bucket = await row.getAttribute("data-bucket");
      const qty = (await row.locator("td").nth(1).innerText()).trim();
      const csvKey = `Contas a Pagar · ${bucket}`;
      expect(csvMap.has(csvKey)).toBeTruthy();
      expect(csvMap.get(csvKey)![1]).toBe(qty);
    }
  });

  test("Export respeita filtro 11495", async ({ page }) => {
    await selectFilialByCode(page, "11495");
    await waitForFinanceCenterLoaded(page);
    const rows = await exportCsvAndRead(page);
    expect(rows.length).toBeGreaterThan(1);
  });

  test("Export respeita filtro 11495,5555", async ({ page }) => {
    await selectFiliaisByCodes(page, ["11495", "5555"]);
    await waitForFinanceCenterLoaded(page);
    const rows = await exportCsvAndRead(page);
    expect(rows.length).toBeGreaterThan(1);
  });

  test("Export respeita Todos (rede)", async ({ page }) => {
    await selectTodosPostos(page);
    await waitForFinanceCenterLoaded(page);
    const rows = await exportCsvAndRead(page);
    expect(rows.length).toBeGreaterThan(5);
  });

  test("PDF abre preview com título do período", async ({ page, context }) => {
    const popupPromise = context.waitForEvent("page");
    await page.locator('[data-testid="fc-export-pdf"]').click();
    const popup = await popupPromise;
    await popup.waitForLoadState("domcontentloaded");
    await expect(popup.locator("h1")).toContainText("Centro Financeiro");
    await popup.close();
  });
});
