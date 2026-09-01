import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";
import {
  approveExpenseDraft,
  confirmExpenseDraft,
  saveExpenseDraft,
} from "./executive_copilot_api.ts";

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
});

function jsonOk(body: unknown, urlCaptured: { url?: string; method?: string }) {
  return (async (input: RequestInfo | URL, init?: RequestInit) => {
    urlCaptured.url = String(input);
    urlCaptured.method = init?.method;
    return {
      ok: true,
      status: 200,
      json: async () => body,
    } as Response;
  }) as typeof fetch;
}

describe("ACT-02 expense draft HTTP client", () => {
  it("Salvar Proposta POST /api/proxy/executive-copilot/action-drafts/expenses", async () => {
    const captured: { url?: string; method?: string } = {};
    globalThis.fetch = jsonOk(
      {
        ok: true,
        draftId: "draft-1",
        actionType: "CREATE_EXPENSE_DRAFT",
        status: "DRAFT",
        unitPublicName: "AP Casa Caiada",
        canExecute: false,
        webpostoWrites: 0,
      },
      captured
    );
    const result = await saveExpenseDraft({
      unitPublicName: "AP Casa Caiada",
      valor: 50,
      descricao: "gelo",
      unidades: [5555],
    });
    assert.equal(captured.method, "POST");
    assert.equal(captured.url, "/api/proxy/executive-copilot/action-drafts/expenses");
    assert.equal(result.draftId, "draft-1");
    assert.equal(result.status, "DRAFT");
    assert.equal(result.canExecute, false);
  });

  it("Confirmar POST .../action-drafts/{id}/confirm", async () => {
    const captured: { url?: string; method?: string } = {};
    globalThis.fetch = jsonOk(
      {
        ok: true,
        draftId: "draft-1",
        actionType: "CREATE_EXPENSE_DRAFT",
        status: "CONFIRMED",
        canExecute: false,
        webpostoWrites: 0,
      },
      captured
    );
    const result = await confirmExpenseDraft("draft-1");
    assert.equal(captured.url, "/api/proxy/executive-copilot/action-drafts/draft-1/confirm");
    assert.equal(result.status, "CONFIRMED");
  });

  it("Aprovar Localmente POST .../action-drafts/{id}/approve", async () => {
    const captured: { url?: string; method?: string } = {};
    globalThis.fetch = jsonOk(
      {
        ok: true,
        draftId: "draft-1",
        actionType: "CREATE_EXPENSE_DRAFT",
        status: "APPROVED_LOCAL",
        canExecute: false,
        webpostoWrites: 0,
      },
      captured
    );
    const result = await approveExpenseDraft("draft-1");
    assert.equal(captured.url, "/api/proxy/executive-copilot/action-drafts/draft-1/approve");
    assert.equal(result.status, "APPROVED_LOCAL");
  });
});
