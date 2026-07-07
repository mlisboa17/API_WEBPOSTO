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

function renderSummary(summary) {
  const s = summary || {};
  if (!s.active_count) {
    return `<p class="muted">Nenhuma solicitação em acompanhamento no momento.</p>`;
  }
  return `
    <dl class="dir-followup-summary">
      <div><dt>Solicitações ativas</dt><dd>${s.active_count}</dd></div>
      <div><dt>Valor em revisão</dt><dd>${fmtMoney(s.total_amount_in_review)}</dd></div>
      <div><dt>Aguardando atribuição</dt><dd>${s.awaiting_assignment_count ?? 0}</dd></div>
    </dl>
    <p class="muted dir-followup-note">Valor em revisão — não constitui perda confirmada.</p>`;
}

function renderFollowUpCard(item) {
  const typeLabel = item.request_type_label || item.title || "Solicitação executiva";
  return `
    <article class="dir-followup-card" data-request-id="${item.request_id}">
      <header>
        <span class="dir-followup-card__tenant">${item.tenant_name || item.tenant_id || "—"}</span>
        <span class="dir-followup-card__status">${item.status_label || item.status}</span>
      </header>
      <h3>${typeLabel}</h3>
      <p class="dir-followup-card__amount">${item.evidence_count} lançamento(s) · ${fmtMoney(item.evidence_total_amount)}</p>
      <p class="muted">Solicitado: ${fmtDateTime(item.requested_at)}</p>
      <p class="muted">Origem: ${item.decision_title || item.decision_category || "Decisão prioritária"}</p>
      <button type="button" class="btn-primary dir-open-followup" data-request-id="${item.request_id}">
        Ver acompanhamento
      </button>
    </article>`;
}

export function renderExecutiveFollowUp(node, payload, filters, options = {}) {
  if (!node) return;

  if (!payload?.data) {
    node.innerHTML = `
      <section class="panel dir-followup">
        <h2>Diretoria — Em acompanhamento</h2>
        <p class="muted">Não foi possível carregar solicitações em acompanhamento.</p>
        <button type="button" id="dirFollowUpRefresh" class="btn-secondary">Tentar novamente</button>
      </section>`;
    node.querySelector("#dirFollowUpRefresh")?.addEventListener("click", () => options.onRefresh?.());
    return;
  }

  const data = payload.data;
  const items = data.items || [];
  const summary = data.summary || {};

  node.innerHTML = `
    <section class="panel dir-followup">
      <header class="dir-home__header">
        <div>
          <h2>Diretoria — Em acompanhamento</h2>
          <p class="muted">Ações executivas que você solicitou ao LOGOS</p>
        </div>
        <button type="button" id="dirFollowUpRefresh" class="btn-secondary">Atualizar</button>
      </header>

      ${renderSummary(summary)}

      ${
        items.length
          ? `<div class="dir-decision-grid">${items.map(renderFollowUpCard).join("")}</div>`
          : `<div class="dir-empty">
              <p>Nenhuma solicitação em acompanhamento</p>
              <p class="muted">Quando você solicitar uma conferência a partir de uma decisão, ela aparecerá aqui.</p>
            </div>`
      }
    </section>`;

  node.querySelector("#dirFollowUpRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelectorAll(".dir-open-followup").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-request-id");
      if (id) options.onOpenFollowUp?.(id);
    });
  });
}
