import { test, expect } from "@playwright/test";
import { gotoFinanceCenter, waitForFinanceCenterLoaded, FC_PERIOD } from "./helpers/financeCenter.helpers";

test.describe("Finance Center — Snapshot First", () => {
  test("fluxo snapshot → render → refresh background", async ({ page }) => {
    const snapshotCalls: { fromSnapshot?: boolean; ms: number }[] = [];

    await page.route("**/api/v1/finance/center/snapshot**", async (route) => {
      const started = Date.now();
      const response = await route.fetch();
      const ms = Date.now() - started;
      const json = await response.json();
      snapshotCalls.push({
        fromSnapshot: json?.data?.fromSnapshot,
        ms,
      });
      await route.fulfill({ response });
    });

    let refreshSeen = false;
    await page.route("**/api/v1/finance/center/refresh**", async (route) => {
      refreshSeen = true;
      await route.continue();
    });

    await gotoFinanceCenter(page);
    await waitForFinanceCenterLoaded(page);

    expect(snapshotCalls.length).toBeGreaterThan(0);
    const badge = page.locator(".finance-center .small").first();
    await expect(badge).toContainText(/Snapshot|Live/);

    await page.waitForTimeout(1500);
    expect(refreshSeen).toBeTruthy();
  });

  test("API snapshot MISS vs HIT (rede)", async ({ request }) => {
    const params = {
      dataInicial: FC_PERIOD.dataInicial,
      dataFinal: FC_PERIOD.dataFinal,
    };

    await request.post("/api/v1/finance/center/refresh", { params });
    await new Promise((r) => setTimeout(r, 8000));

    const hitResp = await request.get("/api/v1/finance/center/snapshot", { params });
    expect(hitResp.ok()).toBeTruthy();
    const hitJson = await hitResp.json();
    expect(hitJson.data.fromSnapshot).toBe(true);

    const missParams = { ...params, empresaCodigo: "5555" };
    const missResp = await request.get("/api/v1/finance/center/snapshot", { params: missParams });
    const missJson = await missResp.json();
    if (!missJson.data.fromSnapshot) {
      await request.post("/api/v1/finance/center/refresh", { params: missParams });
      await new Promise((r) => setTimeout(r, 10000));
      const hit2 = await request.get("/api/v1/finance/center/snapshot", { params: missParams });
      const hit2Json = await hit2.json();
      expect(hit2Json.data.fromSnapshot).toBe(true);
    }
  });
});
