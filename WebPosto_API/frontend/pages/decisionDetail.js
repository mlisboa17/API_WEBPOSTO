import { formatCurrency } from "../services/format.js";

function fmtMoney(value) {
  if (value == null || value === "") return "Indisponível";
  return formatCurrency(value);
}

function fmtCell(value) {
  if (value == null || value === "") return "Indisponível";
  return String(value);
}

const PENDING_STATUSES = new Set(["NO_MATCH", "AMBIGUOUS"]);

function moneyTypeLabel(moneyFound) {
  const atRisk = moneyFound?.at_risk;
  const type = typeof atRisk === "object" ? atRisk?.type : null;
  if (type === "CONFIRMED") return "CONFIRMED";
  if (type === "AT_RISK") return "AT_RISK";
  if (type === "RECOVERABLE_SIGNAL") return "RECOVERABLE_SIGNAL";
  return "ESTIMATED";
}

function moneyTypePhrase(type, aggregate) {
  if (type === "CONFIRMED") return "valor confirmado";
  if (type === "AT_RISK") return "exposição em risco estimada";
  if (type === "RECOVERABLE_SIGNAL") return "sinal de valor recuperável";
  if (aggregate?.anomaly_type === "SUPPLIER_INVOICE_SPIKE") return "valor estimado sob atenção";
  return "valor acima do comportamento de referência";
}

function isSupplierInvoice(aggregate) {
  return aggregate?.anomaly_type === "SUPPLIER_INVOICE_SPIKE";
}

function directorQuestion(aggregate, actions) {
  const list = actions || [];
  const question = list.find((item) => String(item).includes("?"));
  if (question) return question;
  if (aggregate?.nf_number && aggregate?.supplier) {
    return `Por que a NF ${aggregate.nf_number} de ${aggregate.supplier} apareceu neste período sem histórico equivalente no baseline?`;
  }
  return list[0] || null;
}

function renderSupplierContext(aggregate, baseline, meta) {
  if (!isSupplierInvoice(aggregate)) return "";
  const period = meta?.period || {};
  return `
    <section class="dir-block dir-supplier-context">
      <h3>Documento e fornecedor</h3>
      <dl class="dir-detail__kpis">
        <div><dt>NF</dt><dd>${fmtCell(aggregate.nf_number)}</dd></div>
        <div><dt>Fornecedor</dt><dd>${fmtCell(aggregate.supplier)}</dd></div>
        <div><dt>Período</dt><dd>${fmtCell(period.start)} a ${fmtCell(period.end)}</dd></div>
        <div><dt>Período atual</dt><dd>${fmtMoney(baseline.current_value)}</dd></div>
        <div><dt>Período de referência</dt><dd>${fmtMoney(baseline.baseline_value)}</dd></div>
        <div><dt>Detector</dt><dd>${fmtCell(meta?.detector)}</dd></div>
      </dl>
    </section>`;
}

function renderRecommendedActions(actions, aggregate) {
  const list = actions || [];
  if (!list.length) return "";
  const question = directorQuestion(aggregate, list);
  const checks = list.filter((item) => item !== question);
  return `
    <section class="dir-block dir-recommended">
      <h3>O que conferir</h3>
      ${
        question
          ? `<p class="dir-network-question"><strong>Pergunta para o responsável:</strong> ${question}</p>`
          : ""
      }
      ${
        checks.length
          ? `<ul class="dir-checklist">${checks.map((item) => `<li>${item}</li>`).join("")}</ul>`
          : ""
      }
    </section>`;
}

function computePendingReview(items) {
  const list = items || [];
  const pending = list.filter(
    (item) => !item.person_name && PENDING_STATUSES.has(String(item.match_status || "NO_MATCH").toUpperCase()),
  );
  const identified = list.filter((item) => item.person_name);
  return {
    pendingCount: pending.length,
    pendingAmount: pending.reduce((acc, i) => acc + (Number(i.amount) || 0), 0),
    identifiedCount: identified.length,
  };
}

function renderExecutiveReviewBlock(pending, reviewPayload, options, context) {
  const { pendingCount, pendingAmount } = pending;
  const { aggregate, actions, supplierMode } = context;

  if (pendingCount === 0) {
    if (supplierMode && actions?.length) {
      return `
        <section class="panel dir-review-block">
          <h3>Ação executiva</h3>
          <p class="muted">
            Esta decisão possui evidência de NF e fornecedor para encaminhar conferência ao Financeiro
            quando houver lançamentos pendentes de identificação nominal.
          </p>
          <p class="muted dir-review-note">Use as recomendações acima para orientar a conferência — valor estimado, não perda confirmada.</p>
        </section>`;
    }
    return `
      <section class="panel dir-review-block">
        <h3>Identificação nominal</h3>
        <p class="muted">Todos os lançamentos desta decisão possuem beneficiário identificado nas fontes disponíveis.</p>
      </section>`;
  }

  const active = reviewPayload?.data?.active;
  const loading = options.reviewLoading;
  const error = options.reviewError;
  const success = options.reviewSuccess;

  if (active) {
    return `
      <section class="panel dir-review-block dir-review-block--done">
        <h3>Conferência solicitada</h3>
        <p class="dir-review-status">Status: <strong>Aguardando atribuição</strong></p>
        <p class="muted">
          ${active.evidence_count} lançamento(s) · ${fmtMoney(active.evidence_total_amount)}
          em valor sem identificação nominal — requer validação.
        </p>
        <p class="muted dir-review-note">
          Valor em revisão — não constitui perda confirmada. O módulo Financeiro tratará esta solicitação futuramente.
        </p>
      </section>`;
  }

  return `
    <section class="panel dir-review-block">
      <h3>${pendingCount} lançamento(s) precisam de identificação</h3>
      <p>
        ${fmtMoney(pendingAmount)} em lançamentos desta decisão ainda não possuem beneficiário identificado
        nas fontes disponíveis.
      </p>
      <p class="muted dir-review-note">
        Valor sem identificação nominal — requer validação. Não afirma perda financeira confirmada.
      </p>
      ${
        error
          ? `<p class="dir-review-error" role="alert">${error}</p>`
          : ""
      }
      ${
        success
          ? `<p class="dir-review-success" role="status">${success}</p>`
          : ""
      }
      <button type="button" id="dirRequestReviewBtn" class="btn-primary dir-review-cta" ${
        loading ? "disabled" : ""
      }>
        ${loading ? "Solicitando conferência..." : "Solicitar conferência"}
      </button>
    </section>`;
}

function fmtBeneficiary(item) {
  if (item.person_name) return String(item.person_name);
  if (item.match_status === "AMBIGUOUS") {
    return "Mais de um beneficiário possível — requer conferência manual";
  }
  return "Beneficiário não identificado na fonte disponível";
}

function fmtNominalSource(item) {
  if (item.nominal_source) return String(item.nominal_source);
  return "—";
}

function fmtReviewResponsible(item) {
  if (item.review_responsible) return String(item.review_responsible);
  return "Ainda não atribuído";
}

function identityBadge(item) {
  const labels = {
    EXACT: "Identificado",
    PROBABLE: "Provável",
    AMBIGUOUS: "Ambíguo",
    NO_MATCH: "Não identificado",
  };
  const status = item.match_status;
  const label = labels[status] || "Não identificado";
  const cls = {
    EXACT: "exact",
    PROBABLE: "probable",
    AMBIGUOUS: "ambiguous",
    NO_MATCH: "none",
  }[status] || "none";
  return `<span class="dir-match dir-match--${cls}">${label}</span>`;
}

const EXEC_STATUS_LABEL = {
  new: "Criada",
  ready: "Pronta para execução",
  executing: "Em execução",
  completed: "Concluída",
  not_completed: "Não concluída",
  partial: "Parcialmente concluída",
  expired: "Expirada",
  cancelled: "Cancelada",
  archived: "Arquivada",
};

const REJECTION_REASON_LABEL = {
  not_priority: "Não era prioridade",
  no_time: "Não teve tempo",
  incorrect_info: "Informação incorreta",
  already_resolved: "Já resolvido de outra forma",
  could_not_contact: "Não conseguiu contato",
  external_blocker: "Bloqueio externo",
  other: "Outro motivo",
};

const PARTIAL_REASON_LABEL = {
  awaiting_response: "Aguardando resposta externa",
  in_progress: "Em andamento",
  partially_successful: "Parcialmente bem-sucedido",
  requires_followup: "Requer acompanhamento",
};

/** EXEC-02 — bloco "Executar Agora" / confirmação SIM-PARCIAL-NÃO / timeline. */
function renderExecutionBlock(execution, executionUi = {}) {
  const loading = executionUi.loading;
  const error = executionUi.error;
  const success = executionUi.success;
  const form = executionUi.confirmForm || {};

  if (executionUi.notYetExecuted || !execution) {
    return `
      <section class="panel dir-execution-block">
        <h3>Execução</h3>
        <p class="muted">Esta decisão ainda não foi executada.</p>
        ${error ? `<p class="dir-review-error" role="alert">${error}</p>` : ""}
        <button type="button" id="dirExecuteBtn" class="btn-primary" ${loading ? "disabled" : ""}>
          ${loading ? "Executando..." : "Executar Agora"}
        </button>
      </section>`;
  }

  const status = execution.status;
  const statusLabel = EXEC_STATUS_LABEL[status] || status;
  const estimated = execution.estimated_impact || {};
  const confirmed = execution.confirmed_impact || null;
  const timeline = execution.timeline || [];

  const timelineHtml = timeline.length
    ? `<ul class="dir-timeline">${timeline
        .map(
          (e) =>
            `<li><strong>${EXEC_STATUS_LABEL[e.status] || e.status}</strong> — ${fmtCell(e.action)} <span class="muted">(${new Date(e.timestamp).toLocaleString("pt-BR")})</span></li>`,
        )
        .join("")}</ul>`
    : "";

  let confirmationSection = "";
  if (status === "executing") {
    confirmationSection = `
      <div class="dir-confirm-question">
        <p><strong>A decisão resolveu o problema?</strong></p>
        <div class="dir-confirm-choices">
          <button type="button" class="btn-secondary dir-confirm-choice" data-result="yes">SIM</button>
          <button type="button" class="btn-secondary dir-confirm-choice" data-result="partial">PARCIALMENTE</button>
          <button type="button" class="btn-secondary dir-confirm-choice" data-result="no">NÃO</button>
        </div>
        ${
          form.result === "yes"
            ? `
          <div class="dir-confirm-form">
            <label>Valor confirmado (R$)
              <input type="number" step="0.01" id="dirConfirmAmount" value="${form.confirmedAmount ?? ""}" />
            </label>
            <button type="button" id="dirConfirmSubmit" class="btn-primary" ${loading ? "disabled" : ""}>
              ${loading ? "Confirmando..." : "Confirmar SIM"}
            </button>
          </div>`
            : ""
        }
        ${
          form.result === "partial"
            ? `
          <div class="dir-confirm-form">
            <label>Progresso (%)
              <input type="number" min="0" max="100" id="dirConfirmProgress" value="${form.partialProgress ?? ""}" />
            </label>
            <label>Motivo
              <select id="dirConfirmPartialReason">
                <option value="">Selecione...</option>
                ${Object.entries(PARTIAL_REASON_LABEL)
                  .map(([v, l]) => `<option value="${v}" ${form.partialReason === v ? "selected" : ""}>${l}</option>`)
                  .join("")}
              </select>
            </label>
            <label>Valor confirmado até agora (R$) — opcional
              <input type="number" step="0.01" id="dirConfirmAmount" value="${form.confirmedAmount ?? ""}" />
            </label>
            <button type="button" id="dirConfirmSubmit" class="btn-primary" ${loading ? "disabled" : ""}>
              ${loading ? "Confirmando..." : "Confirmar Parcial"}
            </button>
          </div>`
            : ""
        }
        ${
          form.result === "no"
            ? `
          <div class="dir-confirm-form">
            <label>Motivo
              <select id="dirConfirmRejectionReason">
                <option value="">Selecione...</option>
                ${Object.entries(REJECTION_REASON_LABEL)
                  .map(([v, l]) => `<option value="${v}" ${form.rejectionReason === v ? "selected" : ""}>${l}</option>`)
                  .join("")}
              </select>
            </label>
            <button type="button" id="dirConfirmSubmit" class="btn-primary" ${loading ? "disabled" : ""}>
              ${loading ? "Confirmando..." : "Confirmar Não"}
            </button>
          </div>`
            : ""
        }
      </div>`;
  }

  return `
    <section class="panel dir-execution-block">
      <h3>Execução</h3>
      <p>Status: <strong>${statusLabel}</strong></p>
      <dl class="dir-detail__kpis">
        <div><dt>Impacto estimado</dt><dd>${fmtMoney(estimated.amount)} <span class="muted">(${estimated.label || "ESTIMADO"})</span></dd></div>
        ${
          confirmed
            ? `<div><dt>Impacto confirmado</dt><dd>${fmtMoney(confirmed.amount)} <span class="muted">(${confirmed.label})</span></dd></div>`
            : ""
        }
      </dl>
      ${error ? `<p class="dir-review-error" role="alert">${error}</p>` : ""}
      ${success ? `<p class="dir-review-success" role="status">${success}</p>` : ""}
      ${confirmationSection}
      ${timelineHtml}
    </section>`;
}


function renderEvidenceTable(items) {
  if (!items?.length) {
    return `<p class="muted">Nenhum lançamento detalhado disponível para esta decisão.</p>`;
  }

  const rows = items
    .map((item) => {
      const desc = fmtCell(item.description);
      const descShort = desc.length > 80 ? `${desc.slice(0, 80)}…` : desc;
      const itemLimits = item.limitations?.length
        ? `<ul class="dir-item-limits">${item.limitations.map((l) => `<li>${l}</li>`).join("")}</ul>`
        : "";
      return `
        <tr>
          <td>${fmtBeneficiary(item)}</td>
          <td>${fmtCell(item.date)}</td>
          <td>${fmtMoney(item.amount)}</td>
          <td>${fmtCell(item.origin)}</td>
          <td>
            <span class="dir-desc-short">${descShort}</span>
            ${desc.length > 80 ? `<details class="dir-desc-expand"><summary>Ver descrição</summary><p>${desc}</p></details>` : ""}
            ${item.matching_reason ? `<p class="muted dir-match-reason">${item.matching_reason}</p>` : ""}
            ${itemLimits}
          </td>
          <td>${fmtNominalSource(item)}</td>
          <td>${identityBadge(item)}</td>
          <td>${fmtReviewResponsible(item)}</td>
        </tr>`;
    })
    .join("");

  return `
    <div class="dir-evidence-summary">
      <span><strong>${items.length}</strong> lançamento(s)</span>
      <span>Total exibido: <strong>${fmtMoney(items.reduce((acc, i) => acc + (Number(i.amount) || 0), 0))}</strong></span>
    </div>
    <div class="table-scroll">
      <table class="data-table dir-evidence-table">
        <thead>
          <tr>
            <th>Beneficiário</th>
            <th>Data</th>
            <th>Valor</th>
            <th>Origem</th>
            <th>Descrição</th>
            <th>Fonte nominal</th>
            <th>Status de identificação</th>
            <th>Conferência</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

/** EXEC-03 — resumo de métricas de execução do posto (pendentes, hoje, mês, all-time). */
function renderExecutionMetricsBlock(metrics) {
  if (!metrics) return "";
  return `
    <section class="panel dir-execution-metrics">
      <h3>Métricas de execução — ${fmtCell(metrics.tenant_id)}</h3>
      <dl class="dir-detail__kpis">
        <div><dt>Pendentes</dt><dd>${metrics.pending_count} <span class="muted">(${metrics.urgent_count} urgente(s))</span></dd></div>
        <div><dt>Executadas hoje</dt><dd>${metrics.executed_today} <span class="muted">(${metrics.completed_today} concluídas)</span></dd></div>
        <div><dt>Confirmado hoje</dt><dd>${fmtMoney(metrics.confirmed_today_value)}</dd></div>
        <div><dt>Taxa de conclusão (mês)</dt><dd>${Math.round(metrics.period_completion_rate)}%</dd></div>
        <div><dt>Confirmado no mês</dt><dd>${fmtMoney(metrics.period_confirmed_value)}</dd></div>
        <div><dt>Confirmado total</dt><dd>${fmtMoney(metrics.total_confirmed_value)} <span class="muted">(${metrics.total_completed} decisão(ões))</span></dd></div>
      </dl>
    </section>`;
}

export function renderDecisionDetail(node, payload, filters, options = {}) {
  if (!node) return;

  const evidence = payload?.data;
  const reviewPayload = options.reviewRequests;

  if (!evidence) {
    node.innerHTML = `
      <section class="panel">
        <button type="button" id="dirDetailBack" class="btn-link">← Voltar</button>
        <h2>Decisão</h2>
        <p class="muted">Não foi possível carregar os detalhes desta decisão.</p>
      </section>`;
    node.querySelector("#dirDetailBack")?.addEventListener("click", () => options.onBack?.());
    return;
  }

  const meta = evidence.source_metadata || {};
  const baseline = meta.baseline || {};
  const aggregate = meta.evidence_aggregate || {};
  const actions = meta.recommended_actions || [];
  const supplierMode = isSupplierInvoice(aggregate);
  const moneyType = moneyTypeLabel(evidence.money_found);
  const impactValue = evidence.money_found?.at_risk?.value ?? evidence.money_found?.at_risk;
  const excess =
    baseline.current_value != null && baseline.baseline_value != null
      ? Number(baseline.current_value) - Number(baseline.baseline_value)
      : null;

  const nominalMeta = meta.nominal_enrichment || {};
  const prestacaoDisclaimer =
    nominalMeta.prestacao_disclaimer ||
    "A Prestação de Contas foi usada apenas para identificar beneficiários. Ela não substitui conferência financeira externa.";

  const pending = computePendingReview(evidence.evidence_items);

  node.innerHTML = `
    <section class="panel dir-detail">
      <header class="dir-detail__header">
        <button type="button" id="dirDetailBack" class="btn-link">← Voltar à Home</button>
        <button type="button" id="dirDetailRefresh" class="btn-secondary">Atualizar</button>
      </header>

      <h2>Resumo executivo</h2>
      <p class="dir-lead">${evidence.decision_summary || "—"}</p>
      <dl class="dir-detail__kpis">
        <div><dt>Valor sob atenção</dt><dd>${fmtMoney(impactValue)} <span class="muted">(${moneyTypePhrase(moneyType, aggregate)})</span></dd></div>
        <div><dt>Confiança</dt><dd>${evidence.confidence != null ? `${Math.round(evidence.confidence * 100)}%` : "Indisponível"}</dd></div>
        <div><dt>Posto</dt><dd>${fmtCell(meta.tenant_name)}</dd></div>
      </dl>

      ${renderSupplierContext(aggregate, baseline, meta)}

      <section class="dir-block">
        <h3>Por que o LOGOS destacou</h3>
        <p>${evidence.root_cause || "Causa ainda não investigada para este detector."}</p>
        ${
          aggregate.current_count != null
            ? `<p class="muted">${aggregate.current_count} lançamento(s) no período atual vs ${aggregate.baseline_count ?? "—"} no período de referência.</p>`
            : ""
        }
        ${
          supplierMode && aggregate.limitation
            ? `<p class="muted dir-limitation-note">${aggregate.limitation}</p>`
            : ""
        }
      </section>

      ${renderRecommendedActions(actions, aggregate)}

      <section class="dir-block">
        <h3>Evidências da decisão</h3>
        ${
          supplierMode
            ? ""
            : `<p class="dir-prestacao-disclaimer" role="note">${prestacaoDisclaimer}</p>`
        }
        <p class="dir-evidence-intro">
          ${
            supplierMode
              ? "Lançamento(s) que sustentam a NF e o valor sinalizados nesta decisão."
              : excess != null && excess > 0
                ? `Estes são os lançamentos que explicam o aumento de ${fmtMoney(excess)} acima do comportamento de referência.`
                : "Estes são os lançamentos que sustentam esta decisão prioritária."
          }
        </p>
        ${renderEvidenceTable(evidence.evidence_items)}
        ${
          evidence.limitations?.length
            ? `<ul class="dir-limitations">${evidence.limitations.map((l) => `<li>${l}</li>`).join("")}</ul>`
            : ""
        }
      </section>

      ${renderExecutionBlock(options.execution, options.executionUi)}
      ${renderExecutionMetricsBlock(options.executionMetrics)}

      ${renderExecutiveReviewBlock(pending, reviewPayload, options, { aggregate, actions, supplierMode })}
    </section>
  `;

  node.querySelector("#dirDetailBack")?.addEventListener("click", () => options.onBack?.());
  node.querySelector("#dirDetailRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#dirRequestReviewBtn")?.addEventListener("click", () => options.onRequestReview?.());
  node.querySelector("#dirExecuteBtn")?.addEventListener("click", () => options.onExecuteDecision?.());
  node.querySelectorAll(".dir-confirm-choice").forEach((btn) => {
    btn.addEventListener("click", () => options.onSelectConfirmResult?.(btn.getAttribute("data-result")));
  });
  node.querySelector("#dirConfirmSubmit")?.addEventListener("click", () => {
    const form = options.executionUi?.confirmForm || {};
    const amountInput = node.querySelector("#dirConfirmAmount");
    const progressInput = node.querySelector("#dirConfirmProgress");
    const partialReasonSelect = node.querySelector("#dirConfirmPartialReason");
    const rejectionReasonSelect = node.querySelector("#dirConfirmRejectionReason");
    options.onConfirmDecision?.({
      result: form.result,
      confirmedAmount: amountInput?.value ? Number(amountInput.value) : undefined,
      partialProgress: progressInput?.value ? Number(progressInput.value) : undefined,
      partialReason: partialReasonSelect?.value || undefined,
      rejectionReason: rejectionReasonSelect?.value || undefined,
    });
  });
}

