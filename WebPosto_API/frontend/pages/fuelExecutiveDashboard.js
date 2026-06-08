import { renderTable } from "../components/table.js";
import { formatDate, formatMissing, formatNumber } from "../services/format.js";

function toNumber(value) {
  const n = Number(value || 0);
  return Number.isFinite(n) ? n : 0;
}

function pct(value) {
  return `${toNumber(value).toFixed(2)}%`;
}

function litros(value) {
  return `${formatNumber(toNumber(value))} L`;
}

function buildFuelBars(combustiveis) {
  const safe = (combustiveis || []).slice(0, 8);
  const max = Math.max(...safe.map((item) => toNumber(item.litros)), 1);

  return safe
    .map((item) => {
      const height = Math.max(10, Math.round((toNumber(item.litros) / max) * 170));
      return `
        <div style="display:flex;flex-direction:column;align-items:center;gap:6px;">
          <div style="height:170px;display:flex;align-items:flex-end;">
            <div style="width:44px;height:${height}px;border-radius:8px 8px 0 0;background:linear-gradient(180deg,#1b9c85,#0c6a58);"></div>
          </div>
          <div style="font-size:11px;text-align:center;max-width:90px;line-height:1.25;">${formatMissing(item.combustivelDisplay || item.combustivel)}</div>
          <div style="font-size:11px;color:#5a5247;">${litros(item.litros)}</div>
        </div>
      `;
    })
    .join("");
}

function buildCompanyBars(filiais) {
  const safe = (filiais || []).slice(0, 10);
  const max = Math.max(...safe.map((item) => toNumber(item.litros)), 1);

  return safe
    .map((item) => {
      const width = Math.max(4, Math.round((toNumber(item.litros) / max) * 100));
      return `
        <div style="display:grid;grid-template-columns:minmax(180px,1fr) minmax(180px,2fr) 90px;gap:8px;align-items:center;">
          <div style="font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="${formatMissing(item.nomeFilial)}">${formatMissing(item.nomeFilial)}</div>
          <div style="height:12px;border-radius:6px;background:#e7ddcf;overflow:hidden;">
            <div style="height:12px;width:${width}%;background:linear-gradient(90deg,#cd7233,#a4511f);"></div>
          </div>
          <div style="font-size:12px;text-align:right;">${litros(item.litros)}</div>
        </div>
      `;
    })
    .join("");
}

function buildPie(combustiveis) {
  const safe = (combustiveis || []).slice(0, 6);
  const palette = ["#0c6a58", "#df8a2b", "#2f80ed", "#3b6e22", "#c3506e", "#7a59ba"];
  let cursor = 0;
  const parts = safe
    .map((item, idx) => {
      const val = toNumber(item.participacao);
      const start = cursor;
      cursor += val;
      return `${palette[idx % palette.length]} ${start}% ${cursor}%`;
    })
    .join(", ");

  const legend = safe
    .map(
      (item, idx) =>
        `<div style="display:flex;align-items:center;gap:8px;font-size:12px;"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${palette[idx % palette.length]};"></span>${formatMissing(item.combustivelDisplay || item.combustivel)} (${pct(item.participacao)})</div>`
    )
    .join("");

  return `
    <div style="display:flex;gap:14px;align-items:center;flex-wrap:wrap;">
      <div style="width:170px;height:170px;border-radius:50%;background:conic-gradient(${parts || "#ddd 0% 100%"});border:1px solid #e6dbc9;"></div>
      <div style="display:flex;flex-direction:column;gap:6px;">${legend}</div>
    </div>
  `;
}

export function renderFuelExecutiveDashboard(container, payload, options = {}) {
  const data = payload || {};
  const kpis = data.kpis || {};
  const combustiveis = data.combustiveis || [];
  const filiais = data.filiais || [];
  const detalhes = data.detalhes || [];
  const coverageCodes = filiais.map((item) => Number(item.empresaCodigo)).filter((v) => Number.isFinite(v));
  const partialCoverage = coverageCodes.length > 0 && coverageCodes.every((v) => v === 5555 || v === 11495);
  const coverageWarning = partialCoverage
    ? `<section class="state" style="margin-bottom:12px;border-color:#f6d9a5;background:#fff8ea;color:#7a4c06;">Cobertura parcial: dados disponíveis apenas para AP CASA CAIADA e POSTO VIP.</section>`
    : "";

  container.innerHTML = `
    ${coverageWarning}
    <section class="cards" style="margin-bottom:14px;">
      <article class="card"><div class="label">Litros vendidos</div><div class="value">${litros(kpis.litrosVendidos || data.litrosTotal || 0)}</div></article>
      <article class="card"><div class="label">Combustivel lider</div><div class="value" style="font-size:1rem;">${formatMissing(kpis.combustivelLider?.nome)}</div></article>
      <article class="card"><div class="label">Filial lider</div><div class="value" style="font-size:1rem;">${formatMissing(kpis.filialLider?.nomeFilial)}</div></article>
      <article class="card"><div class="label">Participacao Diesel</div><div class="value">${pct(kpis.participacaoDiesel)}</div></article>
      <article class="card"><div class="label">Participacao Gasolina</div><div class="value">${pct(kpis.participacaoGasolina)}</div></article>
      <article class="card"><div class="label">Participacao Etanol</div><div class="value">${pct(kpis.participacaoEtanol)}</div></article>
    </section>

    <section style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px;margin-bottom:14px;">
      <article class="card">
        <div class="label" style="margin-bottom:10px;">Volume por combustivel</div>
        <div style="display:flex;align-items:flex-end;gap:10px;overflow-x:auto;padding-bottom:4px;">${buildFuelBars(combustiveis)}</div>
      </article>
      <article class="card">
        <div class="label" style="margin-bottom:10px;">Volume por filial (Top 10)</div>
        <div style="display:flex;flex-direction:column;gap:9px;">${buildCompanyBars(filiais)}</div>
      </article>
      <article class="card">
        <div class="label" style="margin-bottom:10px;">Participacao %</div>
        ${buildPie(combustiveis)}
      </article>
    </section>

    <section>
      <div id="fuelExecutiveTable"></div>
    </section>
  `;

  const tableNode = container.querySelector("#fuelExecutiveTable");
  const tableRows = detalhes.map((item) => ({
    filial: item.nomeFilial,
    combustivel: item.combustivelDisplay || item.combustivel,
    litros: item.litros,
    participacao: item.participacao,
    data: item.data,
  }));

  renderTable(
    tableNode,
    [
      { key: "filial", label: "Filial", type: "text", sortable: true, filter: true, filterType: "select" },
      { key: "combustivel", label: "Combustivel", type: "text", sortable: true, filter: true, filterType: "select" },
      { key: "litros", label: "Litros", type: "number", sortable: true, filter: true, sum: true, formatter: litros },
      { key: "participacao", label: "Participacao", type: "number", sortable: true, filter: true, formatter: pct },
      { key: "data", label: "Data", type: "date", sortable: true, filter: true, formatter: formatDate },
    ],
    tableRows,
    {
      state: options.tableState,
      onSearchChange: options.onSearchChange,
      onSortChange: options.onSortChange,
      onRefresh: options.onRefresh,
      onClearFilters: options.onClearFilters,
      emptyMessage: "Sem dados de combustiveis para os filtros selecionados.",
      title: "Detalhe por Filial x Combustivel",
      exportName: options.exportName || "painel_executivo_combustiveis",
      pdfDescription: "Volume de litros, participacao e distribuicao por filial e combustivel.",
      showClearFilters: true,
    }
  );
}
