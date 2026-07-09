import { formatCurrency } from "../services/format.js";

function fmtMoney(value) {
  if (value == null || value === "") return "Indisponível";
  return formatCurrency(value);
}

function fmtPct(value) {
  if (value == null || value === "") return "—";
  return `${Math.round(Number(value) * 100)}%`;
}

function detectorLabel(name) {
  const map = {
    FuelRevenueDetector: "Combustível",
    ExpenseDetector: "Despesas",
    CardReceivableDetector: "Recebíveis",
  };
  return map[name] || name;
}

function moneyTypeLabel(action, candidate) {
  const money = candidate?.money_found || action?.money_found || {};
  const atRisk = money?.at_risk?.type || money?.recoverable?.type;
  if (atRisk === "CONFIRMED") return "CONFIRMED";
  return "ESTIMATED";
}

function impactValue(decision) {
  const action = decision?.action || {};
  const candidate = decision?.candidate || {};
  return (
    action.financial_impact?.estimated_value ??
    action.financial_impact?.value ??
    candidate?.money_found?.at_risk?.value ??
    candidate?.financial_impact ??
    null
  );
}

function buildTenantIndex(decisions, observations, tenants) {
  const index = new Map();
  for (const tenant of tenants || []) {
    const id = String(tenant.tenant_id || tenant.empresa_codigo || "");
    index.set(id, {
      tenant_id: id,
      tenant_name: tenant.tenant_name || id,
      detectors: (tenant.detectors_executed || []).map(detectorLabel),
      decisions: [],
      observations: [],
      status: tenant.status || "ANALYZED",
    });
  }
  for (const decision of decisions || []) {
    const id = String(decision.tenant_id || "");
    const row = index.get(id) || {
      tenant_id: id,
      tenant_name: decision.tenant_name || id,
      detectors: [],
      decisions: [],
      observations: [],
      status: "ANALYZED",
    };
    row.decisions.push(decision);
    index.set(id, row);
  }
  for (const obs of observations || []) {
    const id = String(obs.tenant_id || "");
    const row = index.get(id) || {
      tenant_id: id,
      tenant_name: obs.tenant_name || id,
      detectors: [],
      decisions: [],
      observations: [],
      status: "ANALYZED",
    };
    row.observations.push(obs);
    index.set(id, row);
  }
  return [...index.values()];
}

function tenantSummary(row) {
  if (row.decisions.length) {
    const top = row.decisions[0];
    const action = top.action || {};
    return {
      tone: "priority",
      headline: "1 decisão prioritária",
      detail: `${fmtMoney(impactValue(top))} em análise`,
      cta: "Ver decisão",
      ctaKind: "decision",
      targetId: top.decision_id || action.id,
    };
  }
  if (row.observations.length) {
    const top = row.observations[0];
    const gap = top?.evidence?.gap_value ?? top?.financial_impact;
    return {
      tone: "observation",
      headline: `${row.observations.length} sinal(is) em observação`,
      detail: gap ? `${fmtMoney(gap)} em recebíveis/sinais monitorados` : top.title,
      cta: "Ver sinais",
      ctaKind: "observation",
      targetId: null,
    };
  }
  const areas = row.detectors.length ? row.detectors.join(" · ") : "áreas do período";
  return {
    tone: "neutral",
    headline: "Nenhuma decisão prioritária encontrada",
    detail: `Áreas analisadas: ${areas}`,
    cta: null,
    ctaKind: null,
    targetId: null,
  };
}

function renderPriorityHero(decision, options) {
  if (!decision) return "";
  const action = decision.action || {};
  const candidate = decision.candidate || {};
  const id = decision.decision_id || action.id;
  const moneyType = moneyTypeLabel(action, candidate);
  const value = impactValue(decision);
  const evidence = candidate.evidence || action.evidence || {};
  const category = evidence.category || candidate.category || action.category || "—";
  const currentCount = evidence.current_count;
  const baselineCount = evidence.baseline_count;
  const countLine =
    currentCount != null && baselineCount != null
      ? `${currentCount} lançamentos no período · vs ${baselineCount} no período de referência`
      : null;

  return `
    <section class="dir-network-priority">
      <span class="dir-network-eyebrow">Atenção prioritária</span>
      <h3>${decision.tenant_name || decision.tenant_id || "—"}</h3>
      <p class="dir-network-priority__amount">
        ${fmtMoney(value)}
        <span class="dir-money-tag dir-money-tag--${moneyType.toLowerCase()}">${moneyType === "CONFIRMED" ? "confirmado" : "valor estimado acima do comportamento de referência"}</span>
      </p>
      <p class="dir-network-priority__title">${action.title || "Decisão prioritária"}</p>
      <p class="muted">${category}</p>
      ${countLine ? `<p class="muted">${countLine}</p>` : ""}
      <p class="dir-network-confidence">Confiança ${fmtPct(action.confidence ?? candidate.confidence)}</p>
      <button type="button" class="btn-primary dir-open-decision" data-decision-id="${id}">
        Entender decisão
      </button>
    </section>`;
}

function renderTenantCards(rows, options) {
  if (!rows.length) {
    return `<p class="muted">Nenhum posto retornou na cobertura desta análise.</p>`;
  }
  return `
    <div class="dir-network-tenants">
      ${rows
        .map((row) => {
          const summary = tenantSummary(row);
          return `
            <article class="dir-network-tenant dir-network-tenant--${summary.tone}">
              <header>
                <h4>${row.tenant_name || row.tenant_id}</h4>
                <span class="dir-network-tenant__badge">${summary.headline}</span>
              </header>
              <p class="muted">${summary.detail}</p>
              ${
                summary.cta && summary.ctaKind === "decision"
                  ? `<button type="button" class="btn-secondary dir-open-decision" data-decision-id="${summary.targetId}">${summary.cta}</button>`
                  : ""
              }
            </article>`;
        })
        .join("")}
    </div>`;
}

function renderObservations(observations) {
  if (!observations?.length) return "";
  const cards = observations
    .map((obs) => {
      const gap = obs?.evidence?.gap_value ?? obs?.financial_impact;
      return `
        <article class="dir-network-observation">
          <header>
            <span class="dir-network-observation__tag">Sinal em observação</span>
            <span class="dir-network-observation__tenant">${obs.tenant_name || obs.tenant_id}</span>
          </header>
          <h4>${obs.title || "Sinal monitorado"}</h4>
          <p class="muted">${obs.description || ""}</p>
          <dl class="dir-decision-card__meta">
            <div><dt>Valor monitorado</dt><dd>${fmtMoney(gap)}</dd></div>
            <div><dt>Confiança</dt><dd>${fmtPct(obs.confidence)}</dd></div>
          </dl>
          <p class="muted dir-observation-note">${obs.observation_reason || obs.discard_reason || "Ainda abaixo do limiar para decisão prioritária."}</p>
        </article>`;
    })
    .join("");
  return `
    <section class="dir-network-block">
      <h3>Sinais em observação</h3>
      <p class="muted">Monitorados pelo LOGOS — não são decisões prioritárias.</p>
      <div class="dir-network-observation-grid">${cards}</div>
    </section>`;
}

function renderFollowUps(followPayload, options) {
  const items = followPayload?.data?.items || [];
  if (!items.length) {
    return `
      <section class="dir-network-block">
        <h3>Em acompanhamento</h3>
        <p class="muted">Nenhuma solicitação executiva ativa no momento.</p>
      </section>`;
  }
  const cards = items
    .map((item) => {
      const progress =
        item.checked_items_count != null && item.total_items_count
          ? `${item.checked_items_count} de ${item.total_items_count} lançamentos conferidos`
          : null;
      return `
        <article class="dir-network-followup" data-request-id="${item.request_id}">
          <header>
            <span class="dir-network-followup__label">Conferência solicitada</span>
            <span class="dir-network-followup__status">${item.status_label || item.status}</span>
          </header>
          <h4>${item.tenant_name || item.tenant_id}</h4>
          <p>${fmtMoney(item.evidence_total_amount)} em revisão</p>
          <p class="muted">${item.evidence_count} lançamento(s) · ${item.request_type_label || item.title}</p>
          ${
            item.review_responsible
              ? `<p>Responsável: <strong>${item.review_responsible}</strong></p>`
              : `<p class="muted">Aguardando responsável no Financeiro</p>`
          }
          ${progress ? `<p class="dir-network-progress">Progresso: ${progress}</p>` : ""}
          <button type="button" class="btn-secondary dir-open-followup" data-request-id="${item.request_id}">
            Ver acompanhamento
          </button>
        </article>`;
    })
    .join("");
  return `
    <section class="dir-network-block">
      <h3>Em acompanhamento</h3>
      <p class="muted dir-followup-note">Valor em revisão — não constitui perda confirmada.</p>
      <div class="dir-network-followup-grid">${cards}</div>
    </section>`;
}

function renderCoverage(proof, payload) {
  const tenants = proof.tenants || [];
  const detectors = (proof.detectors_executed || []).map(detectorLabel);
  const completedAt = proof.completed_at || payload.last_analysis_at;
  const limitations = proof.limitations || [];
  return `
    <section class="dir-network-coverage">
      <h3>Cobertura da análise</h3>
      <dl class="dir-network-coverage__grid">
        <div><dt>Postos analisados</dt><dd>${proof.tenant_count ?? tenants.length ?? 0}</dd></div>
        <div><dt>Detectores</dt><dd>${detectors.join(" · ") || "—"}</dd></div>
        <div><dt>Última análise</dt><dd>${completedAt ? new Date(completedAt).toLocaleString("pt-BR") : "Em andamento"}</dd></div>
      </dl>
      ${
        limitations.length
          ? `<ul class="dir-network-limitations">${limitations.map((item) => `<li>${item}</li>`).join("")}</ul>`
          : ""
      }
    </section>`;
}

function analysisStatusLine(payload) {
  const status = payload.analysis_status;
  const monitoring = payload.monitoring_state;
  const refresh = payload.refresh_status;
  if (refresh === "RUNNING") return "Atualizando análise da rede…";
  if (status === "PRIORITY_FOUND") return "Decisão prioritária identificada na rede";
  if (monitoring === "OBSERVATION") return "Análise concluída — sinais em observação";
  if (status === "ANALYSIS_COMPLETE_NO_PRIORITY") return "Análise concluída — sem decisão prioritária no período";
  return payload.data?.message || "Aguardando análise";
}

export function renderOwnerDiretoriaHome(node, payload, filters, options = {}) {
  if (!node) return;

  if (!payload?.data) {
    node.innerHTML = `
      <section class="panel dir-home">
        <h2>Visão da rede</h2>
        <p class="muted">Não foi possível carregar a análise no período selecionado.</p>
        <button type="button" id="dirHomeRefresh" class="btn-secondary">Tentar novamente</button>
      </section>`;
    node.querySelector("#dirHomeRefresh")?.addEventListener("click", () => options.onRefresh?.());
    return;
  }

  const data = payload.data;
  const proof = payload.analysis_proof || {};
  const decisions = data.top_5_decisions || [];
  const observations = data.observations || [];
  const priority = decisions[0] || null;
  const tenantRows = buildTenantIndex(decisions, observations, proof.tenants);
  const statusText = analysisStatusLine(payload);

  node.innerHTML = `
    <section class="panel dir-home dir-network">
      <header class="dir-home__header">
        <div>
          <h2>Visão da rede</h2>
          <p class="muted">${statusText}</p>
          <p class="muted">${filters.dataInicial} a ${filters.dataFinal}</p>
        </div>
        <button type="button" id="dirHomeRefresh" class="btn-secondary">Atualizar análise</button>
      </header>

      ${priority ? renderPriorityHero(priority) : ""}

      <section class="dir-network-block">
        <h3>Postos analisados</h3>
        ${renderTenantCards(tenantRows)}
      </section>

      ${renderObservations(observations)}

      ${renderFollowUps(options.followUpPayload, options)}

      ${renderCoverage(proof, payload)}
    </section>
  `;

  node.querySelector("#dirHomeRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelectorAll(".dir-open-decision").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-decision-id");
      if (id) options.onOpenDecision?.(id);
    });
  });
  node.querySelectorAll(".dir-open-followup").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-request-id");
      if (id) options.onOpenFollowUp?.(id);
    });
  });
}
