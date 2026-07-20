import { formatCurrency } from "../services/format.js";
import { EXECUTIVE_UNAVAILABLE_MSG } from "../services/executivePayload.js";

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
    SupplierInvoiceSpikeDetector: "NF fornecedor",
    MarginDetector: "Margem combustível",
  };
  return map[name] || name;
}

function moneyTypeLabel(action, candidate) {
  const money = candidate?.money_found || action?.money_found || {};
  const atRisk = money?.at_risk?.type || money?.recoverable?.type;
  if (atRisk === "CONFIRMED") return "CONFIRMED";
  if (atRisk === "AT_RISK") return "AT_RISK";
  if (atRisk === "RECOVERABLE_SIGNAL") return "RECOVERABLE_SIGNAL";
  return "ESTIMATED";
}

function moneyTypePhrase(type, evidence) {
  const map = {
    CONFIRMED: "valor confirmado",
    ESTIMATED: "valor estimado acima do comportamento de referência",
    AT_RISK: "exposição em risco estimada",
    RECOVERABLE_SIGNAL: "sinal de valor recuperável",
  };
  if (type === "ESTIMATED" && evidence?.anomaly_type === "SUPPLIER_INVOICE_SPIKE") {
    return "valor estimado sob atenção";
  }
  return map[type] || "valor sob atenção";
}

function decisionContext(decision) {
  const action = decision?.action || {};
  const candidate = decision?.candidate || {};
  const evidence = candidate.evidence || action.evidence || {};
  const baseline = candidate.baseline || candidate.baseline_used || {};
  return { action, candidate, evidence, baseline };
}

function evidenceLine(evidence, baseline) {
  const current = baseline.current_value;
  const base = baseline.baseline_value;
  if (evidence.nf_number && evidence.supplier) {
    const baseVal = base != null ? fmtMoney(base) : "R$ 0,00";
    return `NF ${evidence.nf_number} · ${evidence.supplier} — sem despesa equivalente no período de referência (${baseVal})`;
  }
  if (evidence.current_count != null && evidence.baseline_count != null) {
    return `${evidence.current_count} lançamentos no período · vs ${evidence.baseline_count} no período de referência`;
  }
  if (current != null && base != null) {
    return `${fmtMoney(current)} no período atual · vs ${fmtMoney(base)} no período de referência`;
  }
  return evidence.limitation || evidence.category || "";
}

function directorQuestion(decision) {
  const { action, candidate, evidence, baseline } = decisionContext(decision);
  const actions = candidate.recommended_actions || action.recommended_actions || [];
  if (actions.length) return actions[0];
  if (evidence.nf_number && evidence.supplier) {
    return `Por que a NF ${evidence.nf_number} de ${evidence.supplier} apareceu neste período sem histórico equivalente no baseline?`;
  }
  return null;
}

function problemLabel(decision) {
  const { action, candidate, evidence } = decisionContext(decision);
  const detector = candidate.detector || candidate.detector_name || action.detector;
  if (detector === "SupplierInvoiceSpikeDetector" && evidence.nf_number) {
    return `NF ${evidence.nf_number}${evidence.supplier ? ` — ${evidence.supplier}` : ""}`;
  }
  return evidence.category || action.title || candidate.title || "—";
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
    const rank = top.rank ?? row.decisions[0]?.rank;
    const rankLabel = rank ? ` (#${rank} na rede)` : "";
    return {
      tone: "priority",
      headline: row.decisions.length > 1 ? `${row.decisions.length} decisões` : `1 decisão${rankLabel}`,
      detail: `${fmtMoney(impactValue(top))} · ${action.title || "Decisão prioritária"}`,
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

function renderNetworkPriority(decision) {
  if (!decision) return "";
  const { action, candidate, evidence, baseline } = decisionContext(decision);
  const id = decision.decision_id || action.id;
  const moneyType = moneyTypeLabel(action, candidate);
  const value = impactValue(decision);
  const problem = problemLabel(decision);
  const context = evidenceLine(evidence, baseline);

  return `
    <section class="dir-network-hero">
      <span class="dir-network-eyebrow">Prioridade da rede</span>
      <h3>${decision.tenant_name || decision.tenant_id || "—"}</h3>
      <p class="dir-network-priority__amount">
        ${fmtMoney(value)}
        <span class="dir-money-tag dir-money-tag--${moneyType.toLowerCase()}">${moneyTypePhrase(moneyType, evidence)}</span>
      </p>
      <p class="dir-network-priority__title">${action.title || "Decisão prioritária"}</p>
      <p class="muted dir-network-problem">${problem}</p>
      ${context ? `<p class="muted">${context}</p>` : ""}
      <p class="dir-network-confidence">Confiança ${fmtPct(action.confidence ?? candidate.confidence)}</p>
      <button type="button" class="btn-primary dir-open-decision" data-decision-id="${id}">
        Entender prioridade
      </button>
    </section>`;
}

function renderNextDecisions(decisions) {
  const next = (decisions || []).slice(1);
  if (!next.length) return "";
  const cards = next
    .map((decision) => {
      const { action, candidate, evidence, baseline } = decisionContext(decision);
      const id = decision.decision_id || action.id;
      const moneyType = moneyTypeLabel(action, candidate);
      const rank = decision.rank ?? 2;
      const question = directorQuestion(decision);
      const context = evidenceLine(evidence, baseline);
      return `
        <article class="dir-network-next">
          <header>
            <span class="dir-network-next__rank">#${rank} Próxima decisão</span>
            <h4>${decision.tenant_name || decision.tenant_id}</h4>
          </header>
          <p class="dir-network-next__amount">
            ${fmtMoney(impactValue(decision))}
            <span class="dir-money-tag dir-money-tag--${moneyType.toLowerCase()}">${moneyTypePhrase(moneyType, evidence)}</span>
          </p>
          <p class="dir-network-next__title">${problemLabel(decision)}</p>
          ${context ? `<p class="muted">${context}</p>` : `<p class="muted">${action.title || ""}</p>`}
          <p class="muted">Confiança ${fmtPct(action.confidence ?? candidate.confidence)}</p>
          ${
            question
              ? `<p class="dir-network-question"><strong>Pergunta para o responsável:</strong> ${question}</p>`
              : ""
          }
          <button type="button" class="btn-secondary dir-open-decision" data-decision-id="${id}">
            Entender decisão
          </button>
        </article>`;
    })
    .join("");

  return `
    <section class="dir-network-block dir-network-next-section">
      <h3>Próximas decisões</h3>
      <p class="muted">Comparadas e ranqueadas pelo LOGOS — atenção após a prioridade #1.</p>
      <div class="dir-network-next-grid">${cards}</div>
    </section>`;
}

function renderNetworkIntro(decisionCount) {
  if (decisionCount < 2) return "";
  return `
    <p class="dir-network-narrative">
      O LOGOS analisou a rede e encontrou <strong>${decisionCount} decisões reais</strong> —
      comparou as situações e organizou onde olhar primeiro e o que vem depois.
    </p>`;
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
          <p class="muted dir-observation-note">${obs.observation_reason || obs.discard_reason || "O LOGOS ainda não possui evidência suficiente para classificar este sinal como decisão prioritária."}</p>
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

function healthStatusLabel(status) {
  const map = {
    healthy: "Saudável",
    attention: "Atenção",
    risk: "Risco",
    critical: "Crítico",
    unknown: "Indisponível",
  };
  return map[status] || status || "—";
}

function renderBusinessHealth(health) {
  if (!health) return "";
  if (health.unavailable) {
    return `
      <section class="dir-network-block dir-health dir-health--unknown">
        <h3>Saúde da rede</h3>
        <p class="muted">${health.message || EXECUTIVE_UNAVAILABLE_MSG}</p>
      </section>`;
  }

  const tone = health.status || "unknown";
  const deductions = (health.deductions || []).slice(0, 5);
  const deductionList = deductions.length
    ? `<ul class="dir-health-deductions">${deductions
        .map(
          (item) =>
            `<li><strong>${detectorLabel(item.detector)}</strong> · ${item.title || "Anomalia"} · −${item.deduction_points ?? "—"} pts</li>`
        )
        .join("")}</ul>`
    : `<p class="muted">Nenhuma dedução ativa no período.</p>`;

  return `
    <section class="dir-network-block dir-health dir-health--${tone}">
      <h3>Saúde da rede</h3>
      <div class="dir-health-score">
        <span class="dir-health-score__value">${health.overall_score ?? "—"}</span>
        <span class="dir-health-score__label">${healthStatusLabel(health.status)} · ${health.risk_count ?? 0} risco(s)</span>
      </div>
      ${health.message ? `<p class="muted">${health.message}</p>` : ""}
      ${deductionList}
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
  const decisionCount = payload.data?.total_decisions ?? payload.data?.top_5_decisions?.length ?? 0;
  if (refresh === "RUNNING") return "Atualizando análise da rede…";
  if (status === "PRIORITY_FOUND" && decisionCount >= 2) {
    return `${decisionCount} decisões reais identificadas na rede`;
  }
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
  const decisions = (data.top_5_decisions || []).map((item, index) => ({
    ...item,
    rank: item.rank ?? index + 1,
  }));
  const observations = data.observations || [];
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

      ${renderBusinessHealth(payload.businessHealth)}
      ${renderNetworkIntro(decisions.length)}
      ${decisions.length ? renderNetworkPriority(decisions[0]) : ""}
      ${renderNextDecisions(decisions)}

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
