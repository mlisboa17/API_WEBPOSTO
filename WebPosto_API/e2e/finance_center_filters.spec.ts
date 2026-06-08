import { test, expect } from "@playwright/test";
import {
  gotoFinanceCenter,
  selectTodosPostos,
  selectFilialByCode,
  selectFiliaisByCodes,
  clickSelecionarTudo,
  clickLimparSelecao,
  empresaCodigoFromUrl,
  waitForFinanceCenterLoaded,
  FC_PERIOD,
} from "./helpers/financeCenter.helpers";

test.describe("Finance Center — filtros MultiSelectLogos A-F", () => {
  test.beforeEach(async ({ page }) => {
    await gotoFinanceCenter(page);
    await waitForFinanceCenterLoaded(page);
  });

  test("A — Todos os postos → empresaCodigo ausente na URL", async ({ page }) => {
    await selectTodosPostos(page);
    await page.waitForURL((url) => !url.searchParams.has("empresaCodigo"), { timeout: 15_000 });
    expect(empresaCodigoFromUrl(page)).toBeNull();
  });

  test("B — POSTO VIP → empresaCodigo=11495", async ({ page }) => {
    await selectFilialByCode(page, "11495");
    await page.waitForURL(/empresaCodigo=11495/, { timeout: 15_000 });
    expect(empresaCodigoFromUrl(page)).toBe("11495");
  });

  test("C — AP CASA CAIADA → empresaCodigo=5555", async ({ page }) => {
    await selectFilialByCode(page, "5555");
    await page.waitForURL(/empresaCodigo=5555/, { timeout: 15_000 });
    expect(empresaCodigoFromUrl(page)).toBe("5555");
  });

  test("D — VIP + CASA CAIADA → empresaCodigo=11495,5555", async ({ page }) => {
    await selectFiliaisByCodes(page, ["11495", "5555"]);
    await page.waitForURL(/empresaCodigo=11495%2C5555|empresaCodigo=11495,5555/, { timeout: 15_000 });
    const param = empresaCodigoFromUrl(page) || "";
    expect(param.split(",").sort().join(",")).toBe("11495,5555");
  });

  test("E — Selecionar Tudo → lista explícita de filiais", async ({ page }) => {
    await clickSelecionarTudo(page);
    await page.waitForURL(/empresaCodigo=/, { timeout: 15_000 });
    const param = empresaCodigoFromUrl(page) || "";
    expect(param.length).toBeGreaterThan(0);
    expect(param).toContain("11495");
    expect(param).toContain("5555");
  });

  test("F — Limpar Seleção → volta para Todos (sem empresaCodigo)", async ({ page }) => {
    await selectFilialByCode(page, "11495");
    await page.waitForURL(/empresaCodigo=11495/);
    await clickLimparSelecao(page);
    await page.waitForURL((url) => !url.searchParams.has("empresaCodigo"), { timeout: 15_000 });
    expect(empresaCodigoFromUrl(page)).toBeNull();
  });

  test("Datas — período 2026-06-01 a 2026-06-07 refletido na URL", async ({ page }) => {
    const url = new URL(page.url());
    expect(url.searchParams.get("dataInicial")).toBe(FC_PERIOD.dataInicial);
    expect(url.searchParams.get("dataFinal")).toBe(FC_PERIOD.dataFinal);
  });
});
