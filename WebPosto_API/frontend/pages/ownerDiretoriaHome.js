import { formatCurrency } from "../services/format.js";

function fmtMoney(value) {
  if (value == null || value === "") return "Indisponível";
  return formatCurrency(value);
}

function fmtPct(value) {
  if (value == null || value === "") return "—";
  return `${Math.round(Number(value) * 100)}%`;
}

function statusLabel(analysisStatus, monitoringState) {
  if (analysisStatus === "PRIORITY_FOUND") return "Decisão prioritária identificada";
  if (monitoringState === "OBSERVATION") return "Sinais em observação";
  if (analysisStatus === "ANALYSIS_COMPLETE_NO_PRIORITY") return "Análise concluída — sem prioridade";
  return analysisStatus || monitoringState || "Aguardando análise";
}

function renderDecisionCard(decision, onOpen) {
  const action = decision.action || {};
  const id = decision.decision_id || action.id;
  const tenant = decision.tenant_name || decision.tenant_id || "—";
  const impact = action.financial_impact?.estimated_value;
  return `
    <article class="dir-decision-card" data-decision-id="${id}">
      <header>
        <span class="dir-decision-card__rank">#${decision.rank || "—"}</span>
        <span class="dir-decision-card__tenant">${tenant}</span>
      </header>
      <h3>${action.title || "Decisão"}</h3>
      <p class="muted">${action.description || ""}</p>
      <dl class="dir-decision-card__meta">
        <div><dt>Impacto estimado</dt><dd>${fmtMoney(impact)}</dd></div>
        <div><dt>Confiança</dt><dd>${fmtPct(action.confidence)}</dd></div>
      </dl>
      <button type="button" class="btn-primary dir-open-decision" data-decision-id="${id}">
        Abrir decisão
      </button>
    </article>
  `;
}

export function renderOwnerDiretoriaHome(node, payload, filters, options = {}) {
  if (!node) return;

  if (!payload?.data) {
    node.innerHTML = `
      <section class="panel dir-home">
        <h2>Diretoria — Decisões</h2>
        <p class="muted">Não foi possível carregar a análise no período selecionado.</p>
        <button type="button" id="dirHomeRefresh" class="btn-secondary">Tentar novamente</button>
      </section>`;
    node.querySelector("#dirHomeRefresh")?.addEventListener("click", () => options.onRefresh?.());
    return;
  }

  const data = payload.data;
  const decisions = data.top_5_decisions || [];
  const proof = payload.analysis_proof || {};
  const limitations = proof.limitations || [];
  const statusText = statusLabel(payload.analysis_status, payload.monitoring_state);

  node.innerHTML = `
    <section class="panel dir-home">
      <header class="dir-home__header">
        <div>
          <h2>Diretoria — Decisões</h2>
          <p class="muted">${statusText}</p>
        </div>
        <button type="button" id="dirHomeRefresh" class="btn-secondary">Atualizar análise</button>
      </header>

      ${
        decisions.length
          ? `<div class="dir-decision-grid">${decisions.map((d) => renderDecisionCard(d)).join("")}</div>`
          : `<div class="dir-empty">
              <p>${data.message || "Nenhuma decisão prioritária no período analisado."}</p>
              <p class="muted">Áreas verificadas: ${(proof.detectors_executed || []).join(", ") || "—"}</p>
            </div>`
      }

      ${
        limitations.length
          ? `<details class="dir-proof"><summary>O que foi analisado</summary><ul>${limitations
              .map((item) => `<li>${item}</li>`)
              .join("")}</ul></details>`
          : ""
      }
    </section>
  `;

  node.querySelector("#dirHomeRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelectorAll(".dir-open-decision").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-decision-id");
      if (id) options.onOpenDecision?.(id);
    });
  });
}
