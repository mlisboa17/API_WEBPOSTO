import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { normalizeCopilotAnswer } from "./copilot-normalizer.ts";

describe("ACT-02 copilot normalizer", () => {
  it("preserva unitPublicNames e prévia de despesa sem persistir", () => {
    const answer = normalizeCopilotAnswer({
      specialist: "FINANCEIRO",
      answer: "Prévia de despesa.",
      fact: "Proposta CREATE_EXPENSE_DRAFT em DRAFT.",
      units: [118508],
      unitPublicNames: ["Conveniência 24 Horas"],
      suggestedAction: {
        actionType: "CREATE_EXPENSE_DRAFT",
        status: "DRAFT",
        persisted: false,
        unitPublicName: "Conveniência 24 Horas",
        camposPreenchidos: {
          unitPublicName: "Conveniência 24 Horas",
          valor: 80,
          descricao: "gelo",
        },
        executionCode: "ACTION_EXECUTION_NOT_ENABLED",
      },
      webpostoWrites: 0,
    });
    assert.deepEqual(answer.unitPublicNames, ["Conveniência 24 Horas"]);
    assert.equal(answer.actionDraft?.persisted, false);
    assert.equal(answer.actionDraft?.unitPublicName, "Conveniência 24 Horas");
    assert.equal(answer.actionDraft?.canExecute, false);
    assert.equal(
      answer.actionDraft?.filledFields.some((field) => String(field.value).includes("118508")),
      false
    );
  });

  it("não mostra 6666 em unitPublicNames", () => {
    const answer = normalizeCopilotAnswer({
      answer: "ok",
      fact: "fato",
      units: [11495],
      unitPublicNames: ["Posto VIP", "6666"],
      webpostoWrites: 0,
    });
    assert.deepEqual(answer.unitPublicNames, ["Posto VIP"]);
  });
});
