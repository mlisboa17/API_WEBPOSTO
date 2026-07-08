import { formatCurrency } from "../services/format.js";

function fmtMoney(value) {
  if (value == null || value === "") return "Indisponível";
  return formatCurrency(value);
}

function fmtCell(value) {
  if (value == null || value === "") return "Indisponível";
  return String(value);
}

function identityLabel(status) {
  const labels = {
    EXACT: "Identificado",
    PROBABLE: "Provável",
    AMBIGUOUS: "Ambíguo",
    NO_MATCH: "Não identificado",
  };
  return labels[String(status || "NO_MATCH").toUpperCase()] || "Não identificado";
}

function renderEvidenceTable(items) {
  if (!items?.length) {
    return `<p class="muted">Nenhum lançamento pendente vinculado a esta solicitação.</p>`;
  }
  const rows = items
    .map(
      (item) => `
      <tr>
        <td>${fmtCell(item.date)}</td>
        <td>${fmtCell(item.description)}</td>
        <td>${fmtMoney(item.amount)}</td>
        <td>${item.person_name ? fmtCell(item.person_name) : "Não identificado"}</td>
        <td>${fmtCell(item.origin)}</td>
        <td>${fmtCell(item.document_reference || item.source)}</td>
        <td>${identityLabel(item.match_status)}</td>
      </tr>`,
    )
    .join("");
  return `
    <div class="table-scroll">
      <table class="data-table dir-evidence-table">
        <thead>
          <tr>
            <th>Data</th>
            <th>Descrição</th>
            <th>Valor</th>
            <th>Beneficiário</th>
            <th>Origem</th>
            <th>Referência</th>
            <th>Status de identificação</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

function renderAssignSection(item, assignState) {
  const status = String(item.technical_status || "").toUpperCase();
  if (status !== "REQUESTED") {
    if (status === "ASSIGNED" && item.review_responsible) {
      return `
        <section class="dir-block fin-review-assigned">
          <p>Conferência atribuída a <strong>${item.review_responsible}</strong>.</p>
          <p class="muted">Próximas ações operacionais (conferir, documentar, concluir) serão habilitadas em evolução futura.</p>
        </section>`;
    }
    return `
      <section class="dir-block fin-review-waiting">
        <p class="muted">Esta solicitação não está aguardando atribuição.</p>
      </section>`;
  }

  if (assignState?.open) {
    return `
      <section class="dir-block fin-review-assign">
        <h3>Assumir conferência</h3>
        <p class="muted">Quem ficará responsável por esta conferência?</p>
        <label class="fin-assign-label" for="finAssignResponsibleName">Nome do responsável</label>
        <input
          id="finAssignResponsibleName"
          class="fin-assign-input"
          type="text"
          maxlength="200"
          placeholder="Ex.: Marcio de Lima"
          value="${assignState?.name || ""}"
        />
        ${assignState?.error ? `<p class="fin-assign-error">${assignState.error}</p>` : ""}
        <div class="fin-assign-actions">
          <button type="button" id="finAssignConfirm" class="btn-primary" ${assignState?.loading ? "disabled" : ""}>
            ${assignState?.loading ? "Confirmando…" : "Confirmar responsabilidade"}
          </button>
          <button type="button" id="finAssignCancel" class="btn-secondary" ${assignState?.loading ? "disabled" : ""}>
            Cancelar
          </button>
        </div>
      </section>`;
  }

  return `
    <section class="dir-block fin-review-assign">
      <p class="muted">Conferência aguardando responsável.</p>
      <button type="button" id="finAssignOpen" class="btn-primary">Assumir conferência</button>
    </section>`;
}

export function renderFinancialReviewDetail(node, payload, filters, options = {}) {
  if (!node) return;

  const item = payload?.data;
  const assignState = options.assignState || {};

  if (!item) {
    node.innerHTML = `
      <section class="panel">
        <button type="button" id="finReviewDetailBack" class="btn-link">← Voltar</button>
        <h2>Conferência</h2>
        <p class="muted">Não foi possível carregar esta solicitação.</p>
      </section>`;
    node.querySelector("#finReviewDetailBack")?.addEventListener("click", () => options.onBack?.());
    return;
  }

  node.innerHTML = `
    <section class="panel fin-review-detail">
      <header class="dir-detail__header">
        <button type="button" id="finReviewDetailBack" class="btn-link">← Voltar às conferências</button>
        <button type="button" id="finReviewDetailRefresh" class="btn-secondary">Atualizar</button>
      </header>

      ${assignState?.success ? `<p class="fin-assign-success">${assignState.success}</p>` : ""}

      <h2>${item.decision_category || item.decision_title || "Conferência financeira"}</h2>

      <dl class="dir-detail__kpis">
        <div><dt>Posto</dt><dd>${item.tenant_name || item.tenant_id || "—"}</dd></div>
        <div><dt>Origem</dt><dd>${item.origin_label || "Decisão da Diretoria"}</dd></div>
        <div><dt>Decisão</dt><dd>${item.decision_title || item.decision_category || "—"}</dd></div>
        <div><dt>Valor em revisão</dt><dd>${fmtMoney(item.amount_under_review)}</dd></div>
        <div><dt>Status</dt><dd>${item.financial_status_label || item.technical_status}</dd></div>
        <div><dt>Responsável</dt><dd>${item.review_responsible || "Ainda não atribuído"}</dd></div>
      </dl>

      <section class="dir-block">
        <h3>Motivo da conferência</h3>
        <p>${item.reason || "—"}</p>
        <p class="muted fin-inbox-note">Valor em revisão — não constitui perda confirmada.</p>
      </section>

      <section class="dir-block">
        <h3>Itens para conferir (${item.evidence_items_count})</h3>
        ${renderEvidenceTable(item.pending_evidence_items)}
      </section>

      ${renderAssignSection(item, assignState)}
    </section>`;

  node.querySelector("#finReviewDetailBack")?.addEventListener("click", () => options.onBack?.());
  node.querySelector("#finReviewDetailRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#finAssignOpen")?.addEventListener("click", () => options.onAssignOpen?.());
  node.querySelector("#finAssignCancel")?.addEventListener("click", () => options.onAssignCancel?.());
  node.querySelector("#finAssignConfirm")?.addEventListener("click", () => {
    const name = node.querySelector("#finAssignResponsibleName")?.value?.trim();
    options.onAssignConfirm?.(name);
  });
}
