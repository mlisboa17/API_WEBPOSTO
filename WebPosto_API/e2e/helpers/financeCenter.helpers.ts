import { Page, expect } from "@playwright/test";

export const FC_PERIOD = {
  dataInicial: "2026-06-01",
  dataFinal: "2026-06-07",
};

export async function gotoFinanceCenter(page: Page, extraParams: Record<string, string> = {}) {
  const params = new URLSearchParams({
    view: "finance-center",
    dataInicial: FC_PERIOD.dataInicial,
    dataFinal: FC_PERIOD.dataFinal,
    ...extraParams,
  });
  await page.goto(`/app/financial?${params.toString()}`);
  await page.waitForSelector('[data-testid="finance-center-root"]', { timeout: 60_000 });
}

export async function openEmpresaPanel(page: Page) {
  await page.locator("#empresaCodigoToggle").click();
  await expect(page.locator("#empresaCodigoPanel")).not.toHaveAttribute("hidden", "");
}

export async function applyEmpresaSelection(page: Page) {
  await page.locator("#empresaApply").click();
  await page.waitForTimeout(400);
}

export async function selectTodosPostos(page: Page) {
  await openEmpresaPanel(page);
  await page.locator("#empresaCheckAll").check();
  await applyEmpresaSelection(page);
}

export async function selectFilialByCode(page: Page, code: string) {
  await openEmpresaPanel(page);
  await page.locator("#empresaCheckAll").uncheck();
  await page.locator(`#empresaCodigoOptions input[value="${code}"]`).check();
  await applyEmpresaSelection(page);
}

export async function selectFiliaisByCodes(page: Page, codes: string[]) {
  await openEmpresaPanel(page);
  await page.locator("#empresaCheckAll").uncheck();
  for (const code of codes) {
    await page.locator(`#empresaCodigoOptions input[value="${code}"]`).check();
  }
  await applyEmpresaSelection(page);
}

export async function clickSelecionarTudo(page: Page) {
  await openEmpresaPanel(page);
  await page.locator("#empresaSelectAll").click();
  await applyEmpresaSelection(page);
}

export async function clickLimparSelecao(page: Page) {
  await openEmpresaPanel(page);
  await page.locator("#empresaClearAll").click();
  await page.waitForTimeout(400);
}

export function empresaCodigoFromUrl(page: Page): string | null {
  const url = new URL(page.url());
  return url.searchParams.get("empresaCodigo");
}

export async function waitForFinanceCenterLoaded(page: Page) {
  await expect(page.locator(".finance-center .fc-cards .fc-card").first()).toBeVisible();
}

export function parseCsvSemicolon(text: string): string[][] {
  return text
    .trim()
    .split("\n")
    .map((line) => {
      const cells: string[] = [];
      let current = "";
      let inQuotes = false;
      for (let i = 0; i < line.length; i += 1) {
        const ch = line[i];
        if (ch === '"') {
          if (inQuotes && line[i + 1] === '"') {
            current += '"';
            i += 1;
          } else {
            inQuotes = !inQuotes;
          }
        } else if (ch === ";" && !inQuotes) {
          cells.push(current.replace(/^"|"$/g, "").replace(/""/g, '"'));
          current = "";
        } else {
          current += ch;
        }
      }
      cells.push(current.replace(/^"|"$/g, "").replace(/""/g, '"'));
      return cells;
    });
}

export async function scrapeTableTotals(page: Page): Promise<Map<string, string>> {
  const map = new Map<string, string>();
  const rows = page.locator(".finance-center .fc-table-export tbody tr");
  const count = await rows.count();
  for (let i = 0; i < count; i += 1) {
    const cells = rows.nth(i).locator("td");
    const n = await cells.count();
    if (n >= 3) {
      const label = (await cells.nth(0).innerText()).trim();
      const qty = (await cells.nth(1).innerText()).trim();
      const val = (await cells.nth(2).innerText()).trim();
      map.set(label, `${qty}|${val}`);
    }
  }
  return map;
}
