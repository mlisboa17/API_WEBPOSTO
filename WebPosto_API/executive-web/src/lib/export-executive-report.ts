import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";
import * as XLSX from "xlsx";
import type {
  DataAuditFilial,
  DataAuditResponse,
  ExpenseDetailItem,
  UnitsPerformanceResponse,
} from "@/types/api";

function brl(n: number) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(n || 0);
}

function litros(n: number) {
  return `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(n || 0)} L`;
}

export function exportDataAuditPdf(
  audit: DataAuditResponse,
  meta: { filialLabel: string; periodLabel: string }
) {
  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const consolidado = audit.consolidado || {};
  const filiais = audit.filiais || [];

  doc.setFillColor(15, 23, 42);
  doc.rect(0, 0, 595, 72, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(16);
  doc.text("LOGOS | Executive Intelligence", 40, 32);
  doc.setFontSize(10);
  doc.setTextColor(148, 163, 184);
  doc.text("Grupo Lisboa — Relatório Executivo de Aferição / DRE", 40, 50);

  doc.setTextColor(30, 41, 59);
  doc.setFontSize(11);
  doc.text(`Filial: ${meta.filialLabel}`, 40, 100);
  doc.text(`Período: ${meta.periodLabel}`, 40, 116);
  doc.text(
    `Gerado em: ${new Date().toLocaleString("pt-BR")}`,
    40,
    132
  );

  autoTable(doc, {
    startY: 150,
    head: [["KPI", "Valor"]],
    body: [
      ["Faturamento Total", brl(Number(consolidado.faturamentoTotal || 0))],
      ["Volume", litros(Number(consolidado.volumeLitros || 0))],
      ["Abastecimentos", String(consolidado.quantidadeAbastecimentos ?? 0)],
      ["Vales Funcionários", brl(Number(consolidado.valesFuncionariosTotal || 0))],
      ["Resultado Operacional", brl(Number(consolidado.resultadoOperacionalDiario || 0))],
    ],
    theme: "grid",
    headStyles: { fillColor: [37, 99, 235] },
  });

  const planoRows: string[][] = [];
  for (const f of filiais) {
    for (const c of f.despesasPorCategoria || []) {
      planoRows.push([
        f.empresaNome,
        c.categoria,
        String(c.qtd_lancamentos ?? 0),
        brl(c.valor ?? 0),
      ]);
    }
  }

  autoTable(doc, {
    startY: (doc as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 20,
    head: [["Filial", "Plano de Contas", "Lanc.", "Valor"]],
    body: planoRows.length ? planoRows : [["—", "Sem despesas", "0", "R$ 0,00"]],
    theme: "striped",
    headStyles: { fillColor: [15, 23, 42] },
    styles: { fontSize: 8 },
  });

  const pageCount = doc.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setTextColor(100);
    doc.text(
      "Auditoria LOGOS — documento confidencial Grupo Lisboa",
      40,
      820
    );
    doc.text(`Página ${i}/${pageCount}`, 500, 820);
  }

  const nome = `LOGOS_Afericao_${audit.periodo?.inicio || "periodo"}.pdf`;
  doc.save(nome);
}

export function exportDataAuditExcel(audit: DataAuditResponse) {
  const consolidado = audit.consolidado || {};
  const filiais = audit.filiais || [];

  const resumo = [
    ["KPI", "Valor"],
    ["Periodo Inicio", audit.periodo?.inicio || ""],
    ["Periodo Fim", audit.periodo?.fim || ""],
    ["Faturamento Total", Number(consolidado.faturamentoTotal || 0)],
    ["Volume Litros", Number(consolidado.volumeLitros || 0)],
    ["Abastecimentos", Number(consolidado.quantidadeAbastecimentos || 0)],
    ["Resultado Operacional", Number(consolidado.resultadoOperacionalDiario || 0)],
  ];

  const vendas: (string | number)[][] = [
    ["Filial", "Codigo", "Faturamento", "Volume L", "Abastecimentos", "Resultado"],
  ];
  for (const f of filiais) {
    vendas.push([
      f.empresaNome,
      f.empresaCodigo,
      f.faturamentoTotal ?? 0,
      f.volumeLitros ?? 0,
      f.quantidadeAbastecimentos ?? 0,
      f.resultadoOperacionalDiario ?? 0,
    ]);
  }

  const despesas: (string | number)[][] = [
    [
      "Filial",
      "Categoria",
      "Plano Contas",
      "Historico",
      "Fornecedor",
      "NF/Doc",
      "Data",
      "Valor",
    ],
  ];
  for (const f of filiais) {
    for (const cat of f.despesasPorCategoria || []) {
      const itens = (cat.itens || []) as ExpenseDetailItem[];
      if (!itens.length) {
        despesas.push([
          f.empresaNome,
          cat.categoria,
          "",
          "",
          "",
          "",
          "",
          cat.valor ?? 0,
        ]);
        continue;
      }
      for (const item of itens) {
        despesas.push([
          f.empresaNome,
          cat.categoria,
          item.planoContaOficial || item.planoConta || "",
          item.historico || item.descricao || "",
          item.fornecedor || item.favorecido || "",
          item.numeroNF || item.numeroDocumento || "",
          item.dataPagamento || "",
          item.valor ?? 0,
        ]);
      }
    }
  }

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(resumo), "Resumo Diario");
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(vendas), "Vendas por Produto");
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(despesas), "Lancamentos Despesas");
  XLSX.writeFile(wb, `LOGOS_Afericao_${audit.periodo?.inicio || "periodo"}.xlsx`);
}

export function exportUnitsPerformancePdf(
  data: UnitsPerformanceResponse,
  meta: { periodLabel: string }
) {
  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const rede = data.rede || ({} as UnitsPerformanceResponse["rede"]);
  const unidades = data.unidades || [];

  doc.setFillColor(15, 23, 42);
  doc.rect(0, 0, 595, 72, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(16);
  doc.text("LOGOS | Unidades Consolidadas", 40, 32);
  doc.setFontSize(10);
  doc.setTextColor(148, 163, 184);
  doc.text("Margem Operacional + Galonagem — Grupo Lisboa", 40, 50);

  doc.setTextColor(30, 41, 59);
  doc.setFontSize(11);
  doc.text(`Período: ${meta.periodLabel}`, 40, 100);
  doc.text(`Gerado em: ${new Date().toLocaleString("pt-BR")}`, 40, 116);

  autoTable(doc, {
    startY: 140,
    head: [["KPI Rede", "Valor"]],
    body: [
      ["Galonagem", litros(rede.galonagem_total_litros || 0)],
      ["Faturamento", brl(rede.faturamento_total_rs || 0)],
      ["Despesas", brl(rede.despesas_totais_rs || 0)],
      ["Resultado Operacional", brl(rede.resultado_operacional_rs || 0)],
      ["Margem Operacional", `${(rede.margem_media_pct || 0).toFixed(1)}%`],
    ],
    theme: "grid",
    headStyles: { fillColor: [37, 99, 235] },
  });

  autoTable(doc, {
    startY: (doc as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 18,
    head: [["Unidade", "Galonagem", "Faturamento", "Despesas", "Resultado", "Margem %", "Status"]],
    body: unidades.map((u) => [
      u.nome_unidade,
      litros(u.galonagem_litros),
      brl(u.faturamento_total_rs),
      brl(u.despesas_totais_rs),
      brl(u.resultado_operacional_rs),
      `${(u.margem_operacional_pct ?? u.margem_percentual).toFixed(1)}%`,
      u.status_operacional,
    ]),
    theme: "striped",
    headStyles: { fillColor: [15, 23, 42] },
    styles: { fontSize: 8 },
  });

  doc.save(`LOGOS_Unidades_${data.periodo?.inicio || "periodo"}.pdf`);
}

export function exportUnitsPerformanceExcel(data: UnitsPerformanceResponse) {
  const rede = data.rede || ({} as UnitsPerformanceResponse["rede"]);
  const unidades = data.unidades || [];
  const resumo = [
    ["KPI", "Valor"],
    ["Periodo Inicio", data.periodo?.inicio || ""],
    ["Periodo Fim", data.periodo?.fim || ""],
    ["Galonagem Rede L", rede.galonagem_total_litros || 0],
    ["Faturamento Rede", rede.faturamento_total_rs || 0],
    ["Despesas Rede", rede.despesas_totais_rs || 0],
    ["Resultado Operacional", rede.resultado_operacional_rs || 0],
    ["Margem Operacional %", rede.margem_media_pct || 0],
  ];
  const rows: (string | number)[][] = [
    [
      "Unidade",
      "Codigo",
      "Galonagem L",
      "Faturamento",
      "Despesas",
      "Resultado",
      "Margem %",
      "Status",
      "Folha",
      "Cresc. Fat %",
    ],
  ];
  for (const u of unidades) {
    rows.push([
      u.nome_unidade,
      u.unidade_id,
      u.galonagem_litros ?? 0,
      u.faturamento_total_rs ?? 0,
      u.despesas_totais_rs ?? 0,
      u.resultado_operacional_rs ?? 0,
      u.margem_operacional_pct ?? u.margem_percentual ?? 0,
      u.status_operacional,
      u.folha_pagamento_rs ?? 0,
      u.crescimento_faturamento_pct ?? "",
    ]);
  }
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(resumo), "Rede");
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(rows), "Unidades");
  XLSX.writeFile(wb, `LOGOS_Unidades_${data.periodo?.inicio || "periodo"}.xlsx`);
}

export type { DataAuditFilial };
