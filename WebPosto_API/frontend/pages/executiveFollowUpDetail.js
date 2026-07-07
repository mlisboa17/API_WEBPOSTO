import { formatCurrency } from "../services/format.js";

function fmtMoney(value) {
  if (value == null || value === "") return "Indisponível";
  return formatCurrency(value);
}

function fmtDateTime(value) {
  if (!value) return "Indisponível";
  try {
    return new Date(value).toLocaleString("pt-BR");
  } catch {
    return String(value);
  }
}

export function renderExecutiveFollowUpDetail(node, payload, filters, options = {}) {
  if (!node) return;

  const item = payload?.data;

  if (!item) {
    node.innerHTML = `
      <section class="panel">
        <button type="button" id="dirFollowUpDetailBack" class="btn-link">← Voltar</button>
        <h2>Acompanhamento</h2>
        <p class="muted">Não foi possível carregar esta solicitação.</p>
      </section>`;
    node.querySelector("#dirFollowUpDetailBack")?.addEventListener("click", () => options.onBack?.());
    return;
  }

  const reason =
    item.description ||
    `${item.evidence_count} lançamento(s) desta decisão não possuem beneficiário identificado nas fontes disponíveis.`;

  node.innerHTML = `
    <section class="panel dir-followup-detail">
      <header class="dir-detail__header">
        <button type="button" id="dirFollowUpDetailBack" class="btn-link">← Voltar ao acompanhamento</button>
        <button type="button" id="dirFollowUpDetailRefresh" class="btn-secondary">Atualizar</button>
      </header>

      <h2>${item.request_type_label || item.title || "Conferência executiva"}</h2>

      <dl class="dir-detail__kpis">
        <div><dt>Posto</dt><dd>${item.tenant_name || item.tenant_id || "—"}</dd></div>
        <div><dt>Status</dt><dd>${item.status_label || item.status}</dd></div>
        <div><dt>Solicitado em</dt><dd>${fmtDateTime(item.requested_at)}</dd></div>
        <div><dt>Valor em revisão</dt><dd>${fmtMoney(item.evidence_total_amount)}</dd></div>
        <div><dt>Itens</dt><dd>${item.evidence_count} lançamento(s)</dd></div>
      </dl>

      <section class="dir-block">
        <h3>Origem da solicitação</h3>
        <p><strong>Decisão:</strong> ${item.decision_title || item.decision_category || "—"}</p>
      </section>

      <section class="dir-block">
        <h3>Motivo</h3>
        <p>${reason}</p>
        <p class="muted dir-followup-note">Valor em revisão — não constitui perda confirmada.</p>
      </section>

      <section class="dir-block">
        <h3>Responsável pela conferência</h3>
        <p>${item.review_responsible || "Ainda não atribuído"}</p>
      </section>

      <section class="dir-block">
        <h3>Ação disponível</h3>
        <button type="button" id="dirOpenOriginalDecision" class="btn-primary">
          Ver decisão original
        </button>
      </section>
    </section>`;

  node.querySelector("#dirFollowUpDetailBack")?.addEventListener("click", () => options.onBack?.());
  node.querySelector("#dirFollowUpDetailRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#dirOpenOriginalDecision")?.addEventListener("click", () => {
    if (item.decision_id) options.onOpenDecision?.(item.decision_id);
  });
}
