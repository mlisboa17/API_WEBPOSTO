import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { COPILOT_PUBLIC_UNITS } from "../../types/executive_copilot.ts";
import {
  blockedFriendlyMessage,
  canApproveExpenseProposal,
  canConfirmExpenseProposal,
  canSaveExpenseProposal,
  displayUnitNames,
  hideFuelMetrics,
  neverExposeTechnicalCode,
  publicNameForCode,
  unitsForAsk,
} from "./expense-draft-ui.ts";

describe("ACT-02 copilot public units", () => {
  it("expõe só os quatro nomes públicos e nunca 6666", () => {
    const names = COPILOT_PUBLIC_UNITS.map((unit) => unit.publicName);
    assert.deepEqual(names, [
      "AP Casa Caiada",
      "Posto VIP",
      "Posto Real/Doze",
      "Conveniência 24 Horas",
    ]);
    assert.equal(
      COPILOT_PUBLIC_UNITS.some((unit) => String(unit.code) === "6666" || unit.publicName.includes("6666")),
      false
    );
  });

  it("mapeia 6666 para Posto VIP e não devolve código técnico", () => {
    assert.equal(publicNameForCode(6666), "Posto VIP");
    assert.equal(neverExposeTechnicalCode(5555), "AP Casa Caiada");
    assert.equal(neverExposeTechnicalCode("6666"), "Posto VIP");
    assert.equal(displayUnitNames(["AP Casa Caiada", "Posto VIP"]), "AP Casa Caiada, Posto VIP");
  });
});

describe("ACT-02 expense draft actions", () => {
  it("desabilita Salvar Proposta em Todas as Unidades", () => {
    assert.equal(
      canSaveExpenseProposal({
        actionType: "CREATE_EXPENSE_DRAFT",
        isAllUnits: true,
        persisted: false,
      }),
      false
    );
    assert.equal(
      canSaveExpenseProposal({
        actionType: "CREATE_EXPENSE_DRAFT",
        isAllUnits: false,
        persisted: false,
      }),
      true
    );
    assert.equal(
      canSaveExpenseProposal({
        actionType: "CREATE_EXPENSE_DRAFT",
        isAllUnits: false,
        draftId: "abc",
        persisted: true,
        status: "DRAFT",
      }),
      false
    );
  });

  it("Confirmar só no DRAFT persistido e Aprovar Localmente só para diretor/admin/owner", () => {
    assert.equal(canConfirmExpenseProposal({ draftId: "d1", status: "DRAFT" }), true);
    assert.equal(canConfirmExpenseProposal({ draftId: "d1", status: "CONFIRMED" }), false);
    assert.equal(canApproveExpenseProposal({ draftId: "d1", status: "CONFIRMED", role: "director" }), true);
    assert.equal(canApproveExpenseProposal({ draftId: "d1", status: "CONFIRMED", role: "manager" }), false);
    assert.equal(canApproveExpenseProposal({ draftId: "d1", status: "APPROVED_LOCAL", role: "admin" }), false);
  });

  it("Todas as Unidades envia unidades vazias para o backend expandir o escopo autorizado", () => {
    assert.deepEqual(unitsForAsk({ kind: "all", publicName: "Todas as Unidades" }), []);
    assert.deepEqual(
      unitsForAsk({ kind: "unit", publicName: "Conveniência 24 Horas", code: 118508 }),
      [118508]
    );
  });
});

describe("ACT-02 blocked copy", () => {
  it("sugere duas unidades compatíveis na comparação e esconde métricas de combustível na loja", () => {
    const copy = blockedFriendlyMessage("COMPARISON_REQUIRES_MULTIPLE_UNITS", "msg backend");
    assert.match(copy, /pelo menos duas unidades compatíveis/);
    assert.equal(hideFuelMetrics("UNIT_SOURCE_NOT_APPLICABLE"), true);
    assert.equal(
      blockedFriendlyMessage(
        "UNIT_SOURCE_NOT_APPLICABLE",
        "Esta fonte de combustível não se aplica à Conveniência 24 Horas."
      ),
      "Esta fonte de combustível não se aplica à Conveniência 24 Horas."
    );
  });
});
