import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";
import * as XLSX from "xlsx";
import type { DataAuditFilial, DataAuditResponse, ExpenseDetailItem } from "@/types/api";

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

export type { DataAuditFilial };
