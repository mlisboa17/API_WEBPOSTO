/**
 * Dossiê Legal de Auditoria Anti-Fraude — laudo pericial corporativo (PDF).
 * Cadeia de custódia (SHA-256) + mascaramento PCI-DSS / LGPD + termo Art. 482 CLT.
 */

import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";
import type { CardFraudBicoDetalhe, CardFraudOcorrencia } from "@/types/api";
import { FILIAIS_CONFIG } from "@/config/filiais_config";

/** CNPJs cadastrais do Grupo Lisboa (exibição institucional no laudo). */
const FILIAL_CNPJ: Record<number, string> = {
  5555: "00.000.000/0001-55",
  11495: "00.000.000/0001-14",
  74014: "00.000.000/0001-74",
};

function brl(n: number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(n || 0);
}

function litros3(n: number) {
  return `${(n ?? 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3,
  })} L`;
}

function rsL4(n: number) {
  return `${(n ?? 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 4,
    maximumFractionDigits: 4,
  })}/L`;
}

function formatHora(iso?: string) {
  if (!iso) return "—";
  if (iso.includes("T")) return iso.split("T")[1]?.slice(0, 8) || iso;
  if (iso.includes(" ")) return iso.split(" ")[1]?.slice(0, 8) || iso;
  return iso.slice(0, 8);
}

function formatDataHora(iso?: string) {
  if (!iso) return "—";
  const raw = iso.trim();
  const [datePart, timePart] = raw.includes("T")
    ? raw.split("T")
    : raw.includes(" ")
      ? raw.split(" ")
      : [raw, ""];
  const d = datePart?.slice(0, 10) || "";
  const t = (timePart || "").slice(0, 8);
  if (d && t) {
    const [y, m, day] = d.split("-");
    return `${day}/${m}/${y} ${t}`;
  }
  return formatHora(iso);
}

/** PCI-DSS: mascara PAN — exibe apenas últimos 4 dígitos. */
export function maskPanPci(finalDigits?: string | null): string {
  const last4 = (finalDigits || "").replace(/\D/g, "").slice(-4);
  if (!last4) return "**** **** **** ****";
  return `**** **** **** ${last4}`;
}

/** LGPD: mascara CPF mantendo os 2 primeiros e 2 últimos dígitos. */
export function maskCpfLgpd(cpf?: string | null): string {
  const d = (cpf || "").replace(/\D/g, "");
  if (!d || d.length < 4) return "***.***.***-**";
  if (d.length >= 11) {
    return `${d.slice(0, 3)}.***.***-${d.slice(-2)}`;
  }
  return `${d.slice(0, 2)}******${d.slice(-2)}`;
}

function detalhesOf(o: CardFraudOcorrencia): CardFraudBicoDetalhe[] {
  if (o.abastecimentosAgrupados?.length) return o.abastecimentosAgrupados;
  return o.detalhes || [];
}

function descontoPorLitro(o: CardFraudOcorrencia): number {
  if (o.descontoPorLitro != null && Number.isFinite(o.descontoPorLitro)) {
    return o.descontoPorLitro;
  }
  const desc = o.valorDesconto ?? 0;
  const litros = o.litros ?? 0;
  return litros > 0 ? desc / litros : 0;
}

function isCartaoRepetido(o: CardFraudOcorrencia): boolean {
  return !!(o.cartaoRepetido ?? o.cartao_repetido);
}

function qtdUso(o: CardFraudOcorrencia): number {
  return o.quantidadeUsoCartao ?? o.quantidade_uso_cartao ?? 0;
}

function qtdAbastCartao(o: CardFraudOcorrencia): number {
  return o.quantidadeAbastecimentosCartao ?? qtdUso(o);
}

function severidadeLabel(o: CardFraudOcorrencia): string {
  const score = o.scoreGravidade ?? 0;
  const nivel = (o.nivelRisco || "").toUpperCase();
  const curinga = isCartaoRepetido(o);
  if (score >= 100 || curinga) {
    return `CRÍTICO MÁXIMO [${score}/100] — Cartão Curinga / Retenção de Numerário`;
  }
  if (nivel === "ALTO" || nivel === "CRITICO" || score >= 80) {
    return `CRÍTICO [${score}/100] — Retenção / Agrupamento eletrônico`;
  }
  if (nivel === "DESCONTO" || score >= 60) {
    return `DESCONTO / ABUSO [${score}/100] — Fidelidade/App/CPF`;
  }
  if (nivel === "MEDIO" || score >= 40) {
    return `MÉDIO [${score}/100] — Atenção operacional`;
  }
  return `BAIXO [${score}/100] — Monitoramento`;
}

function canonicalPayload(o: CardFraudOcorrencia): string {
  const rows = detalhesOf(o).map((d) => ({
    id: d.idAbastecimento ?? d.abastecimentoId,
    bico: d.bico,
    litros: d.litros,
    valor: d.valorTotal ?? d.valor,
    t1: d.dataHoraBico || d.horaBico,
    ret: d.tempoRetencaoMinutos,
  }));
  return JSON.stringify({
    id: o.idOcorrencia || o.id,
    venda: o.vendaCodigo,
    empresa: o.empresaCodigo || o.postoUnidade,
    frentista: o.frentistaId ?? o.funcionarioId,
    t1: o.dataHoraBico || o.horaBico,
    t2: o.dataHoraEmissaoCupom || o.dataHoraBaixa || o.horaBaixa,
    retencao: o.tempoRetencaoMinutos,
    valor: o.valorTotal ?? o.valorTotalCartao,
    desconto: o.valorDesconto,
    final: (o.cartaoFinal || "").replace(/\D/g, "").slice(-4),
    nsu: o.cartaoNsu || "",
    bicos: rows,
    score: o.scoreGravidade,
    gatilho: o.gatilho,
  });
}

export async function sha256Hex(text: string): Promise<string> {
  const data = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function yAfterTable(doc: jsPDF, fallback: number): number {
  const last = (doc as unknown as { lastAutoTable?: { finalY: number } }).lastAutoTable;
  return (last?.finalY ?? fallback) + 16;
}

function ensureSpace(doc: jsPDF, y: number, need: number): number {
  if (y + need > 780) {
    doc.addPage();
    return 48;
  }
  return y;
}

/**
 * Gera e baixa o PDF do dossiê legal da ocorrência.
 */
export async function exportFraudLegalDossierPdf(
  o: CardFraudOcorrencia,
  opts?: { outrasBaixasOperador?: number }
): Promise<{ hash: string; filename: string }> {
  const hash = await sha256Hex(canonicalPayload(o));
  const emp = Number(o.empresaCodigo || o.postoUnidade || 0);
  const filialCfg = FILIAIS_CONFIG[emp];
  const filialNome =
    o.postoNome || o.empresaNome || filialCfg?.nome || `Filial ${emp || "—"}`;
  const cnpj = FILIAL_CNPJ[emp] || "—.—.—/—.—";
  const emitidoEm = new Date().toLocaleString("pt-BR", {
    timeZone: "America/Recife",
  });
  const oid = o.idOcorrencia || o.id;
  const t1 = o.dataHoraBico || o.dataHora || o.horaBico || "";
  const t2 = o.dataHoraEmissaoCupom || o.dataHoraBaixa || o.horaBaixa || "";
  const detalhes = detalhesOf(o);
  const outrasBaixas = opts?.outrasBaixasOperador ?? 0;

  const doc = new jsPDF({ unit: "pt", format: "a4" });

  // ── Cabeçalho institucional ──
  doc.setFillColor(15, 23, 42);
  doc.rect(0, 0, 595, 88, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(13);
  doc.text("WebPosto LOGOS — Auditoria & Compliance Operacional", 40, 28);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.setTextColor(203, 213, 225);
  doc.text("DOSSIÊ LEGAL DE AUDITORIA · Laudo Pericial Corporativo", 40, 46);
  doc.text("Cadeia de Custódia · PCI-DSS · LGPD · Art. 482 CLT", 40, 60);
  doc.setFontSize(8);
  doc.text(`Emissão: ${emitidoEm}`, 40, 76);
  doc.text(`Ocorrência: ${oid}`, 360, 76);

  let y = 108;
  doc.setTextColor(15, 23, 42);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.text("1. Cadeia de Custódia & Autenticidade", 40, y);
  y += 14;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.text(`Unidade/Filial: ${filialNome} (${emp || "—"})`, 40, y);
  y += 12;
  doc.text(`CNPJ: ${cnpj}`, 40, y);
  y += 12;
  doc.text(`Data/Hora da emissão do laudo: ${emitidoEm}`, 40, y);
  y += 12;
  doc.setFont("helvetica", "bold");
  doc.setTextColor(127, 29, 29);
  doc.text("Código Único de Autenticidade (SHA-256):", 40, y);
  y += 12;
  doc.setFont("courier", "normal");
  doc.setFontSize(7.5);
  doc.setTextColor(30, 41, 59);
  const hashLines = doc.splitTextToSize(hash, 515);
  doc.text(hashLines, 40, y);
  y += hashLines.length * 10 + 10;

  // ── Resumo da infração ──
  y = ensureSpace(doc, y, 80);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.setTextColor(15, 23, 42);
  doc.text("2. Resumo da Infração & Classificação de Risco", 40, y);
  y += 8;

  autoTable(doc, {
    startY: y,
    head: [["Campo", "Valor"]],
    body: [
      ["Severidade / Score", severidadeLabel(o)],
      ["Gatilho", o.gatilho || "—"],
      ["Motivo técnico", (o.motivoSuspeita || "—").slice(0, 280)],
      [
        "Operador / Frentista",
        `${o.funcionarioNome || o.frentistaNome || "—"} (matrícula/ID: ${
          o.frentistaId ?? o.funcionarioId ?? "—"
        })`,
      ],
      [
        "Terminal / PDV / Turno",
        "Não informado no feed WebPosto (baixa sem PDV explícito)",
      ],
      ["Código da venda", String(o.vendaCodigo || "—")],
    ],
    theme: "grid",
    headStyles: { fillColor: [127, 29, 29], textColor: 255, fontSize: 8 },
    styles: { fontSize: 8, cellPadding: 4 },
    columnStyles: { 0: { cellWidth: 130 }, 1: { cellWidth: 385 } },
  });
  y = yAfterTable(doc, y);

  // ── Quadro de evidências ──
  y = ensureSpace(doc, y, 100);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.setTextColor(15, 23, 42);
  doc.text("3. Quadro de Evidências Temporais & Financeiras (PCI-DSS / LGPD)", 40, y);
  y += 8;

  autoTable(doc, {
    startY: y,
    head: [["Evidência", "Valor"]],
    body: [
      ["Hora da Puxada (T₁)", formatDataHora(t1)],
      ["Hora da Emissão / Baixa (T₂)", formatDataHora(t2)],
      ["Tempo de Retenção (ΔT)", `${o.tempoRetencaoMinutos ?? 0} min`],
      ["Valor Total (R$)", brl(o.valorTotal ?? o.valorTotalCartao ?? 0)],
      ["Desconto Aplicado (R$)", brl(o.valorDesconto ?? 0)],
      ["Desconto / Litro (R$/L)", rsL4(descontoPorLitro(o))],
      ["Litros totais", litros3(o.litros ?? 0)],
      ["CPF vinculado (LGPD)", maskCpfLgpd(o.cpfDesconto)],
      ["Forma de Pagamento", o.formaPagamento || o.meioPagamento || "—"],
      ["Adquirente / Canal", o.meioPagamento || o.formaPagamento || "—"],
      ["Bandeira", o.cartaoBandeira || "—"],
      ["Cartão (PCI-DSS)", maskPanPci(o.cartaoFinal)],
      ["NSU", o.cartaoNsu || "—"],
      ["Autorização TEF", o.cartaoAutorizacao || "—"],
    ],
    theme: "striped",
    headStyles: { fillColor: [15, 23, 42], textColor: 255, fontSize: 8 },
    styles: { fontSize: 8, cellPadding: 3.5 },
    columnStyles: { 0: { cellWidth: 160 }, 1: { cellWidth: 355 } },
  });
  y = yAfterTable(doc, y);

  // ── Prova de dolo / recorrência ──
  if (isCartaoRepetido(o)) {
    y = ensureSpace(doc, y, 90);
    doc.setFillColor(254, 226, 226);
    doc.setDrawColor(185, 28, 28);
    doc.roundedRect(40, y, 515, 72, 4, 4, "FD");
    doc.setTextColor(127, 29, 29);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10);
    doc.text("4. Destaque de Prova de Dolo & Recorrência — CARTÃO CURINGA", 48, y + 16);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8.5);
    const alerta = doc.splitTextToSize(
      `Alerta de Rotatividade: o cartão ${o.cartaoBandeira || "Cartão"} ${maskPanPci(
        o.cartaoFinal
      )} foi utilizado para baixar ${qtdAbastCartao(o)} abastecimento(s) diferente(s) ` +
        `em ${qtdUso(o)} baixa(s)/ocorrência(s) no período. Possível uso de cartão próprio/curinga na pista. ` +
        `Outras baixas normais do mesmo operador no período (contexto): ${outrasBaixas}.`,
      500
    );
    doc.text(alerta, 48, y + 34);
    y += 88;
  } else {
    y = ensureSpace(doc, y, 40);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(11);
    doc.setTextColor(15, 23, 42);
    doc.text("4. Destaque de Prova de Dolo & Recorrência", 40, y);
    y += 12;
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    doc.text(
      `Sem flag de cartão repetido nesta ocorrência. Outras baixas do operador no período: ${outrasBaixas}.`,
      40,
      y
    );
    y += 18;
  }

  // ── Bicos ──
  y = ensureSpace(doc, y, 80);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.setTextColor(15, 23, 42);
  doc.text("5. Detalhamento dos Bicos Envolvidos", 40, y);
  y += 8;

  const bicoRows = detalhes.length
    ? detalhes.map((d) => {
        const bico = String(d.bico ?? 0).padStart(2, "0");
        const bomba = String(
          d.bomba && d.bomba > 0
            ? d.bomba
            : Math.floor((Math.max(1, d.bico || 1) - 1) / 2) + 1
        ).padStart(2, "0");
        const tab = d.precoTabela ?? d.precoUnitario ?? 0;
        const prat = d.precoPraticado ?? d.precoUnitario ?? 0;
        return [
          `Bico ${bico} - Bomba ${bomba}`,
          formatHora(d.dataHoraBico || d.horaBico),
          `${d.tempoRetencaoMinutos ?? 0} min`,
          litros3(d.litros ?? 0),
          brl(tab),
          brl(prat),
          brl(d.valorDesconto ?? 0),
        ];
      })
    : [["—", "—", "—", "—", "—", "—", "—"]];

  autoTable(doc, {
    startY: y,
    head: [["Bico/Bomba", "T₁ Abast.", "ΔT", "Volume", "Tabela", "Praticado", "Desc."]],
    body: bicoRows,
    theme: "grid",
    headStyles: { fillColor: [30, 64, 175], textColor: 255, fontSize: 7 },
    styles: { fontSize: 7, cellPadding: 3 },
  });
  y = yAfterTable(doc, y);

  // ── Termo legal ──
  y = ensureSpace(doc, y, 220);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.setTextColor(15, 23, 42);
  doc.text("6. Termo Legal & Enquadramento Trabalhista (Art. 482 CLT)", 40, y);
  y += 14;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(8);
  const parecer = doc.splitTextToSize(
    "PARECER TÉCNICO DE AUDITORIA: Com base nas evidências temporais, financeiras e " +
      "eletrônicas (TEF) consolidadas neste dossiê — inclusive eventual recorrência de " +
      "cartão (Cartão Curinga) e retenção anormal de abastecimentos —, a conduta apurada " +
      "pode configurar, em tese, hipótese de justa causa por improbidade e/ou mau " +
      "procedimento, nos termos do art. 482, alíneas \"a\" e \"b\", da Consolidação das " +
      "Leis do Trabalho (CLT). Este documento integra a cadeia de custódia digital do " +
      "Grupo Lisboa / WebPosto LOGOS e destina-se a suporte de auditoria interna, " +
      "compliance e eventual instrução disciplinar, observando PCI-DSS (mascaramento de " +
      "PAN) e LGPD (minimização/mascaramento de dados pessoais).",
    515
  );
  doc.text(parecer, 40, y);
  y += parecer.length * 10 + 16;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(9);
  doc.text("Campos de assinatura / ciência:", 40, y);
  y += 18;

  const signBox = (label: string, yy: number) => {
    doc.setDrawColor(100, 116, 139);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    doc.text(label, 40, yy);
    doc.line(40, yy + 28, 270, yy + 28);
    doc.setFontSize(7);
    doc.setTextColor(100, 116, 139);
    doc.text("Nome / Assinatura", 40, yy + 38);
    doc.text("CPF: ____________________", 40, yy + 50);
    doc.text("Data: ____/____/________", 160, yy + 50);
    doc.setTextColor(15, 23, 42);
  };

  y = ensureSpace(doc, y, 200);
  signBox("Auditor / Gerente de Compliance", y);
  signBox("Testemunha 1", y + 70);
  y += 140;
  y = ensureSpace(doc, y, 140);
  signBox("Testemunha 2", y);
  signBox("Ciente do Funcionário Auditado", y + 70);

  // Rodapé em todas as páginas
  const pageCount = doc.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(7);
    doc.setTextColor(100, 116, 139);
    doc.text(
      "CONFIDENCIAL — WebPosto LOGOS · Cadeia de Custódia · Uso exclusivo Compliance/RH",
      40,
      820
    );
    doc.text(`Hash: ${hash.slice(0, 16)}…`, 40, 832);
    doc.text(`Página ${i}/${pageCount}`, 500, 820);
  }

  const filename = `LOGOS_Dossie_Legal_${oid}_${emp || "rede"}.pdf`;
  doc.save(filename);
  return { hash, filename };
}
