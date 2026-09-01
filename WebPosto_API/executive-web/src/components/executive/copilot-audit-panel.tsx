"use client";

import React, { useState } from "react";
import {
  ShieldCheck,
  X,
  FileCheck2,
  GitBranch,
  CheckCircle2,
  AlertTriangle,
  Lock,
  Building2,
  Calendar,
  Layers,
  Database,
  Info,
} from "lucide-react";
import { CopilotAnswer, EvidenceItem, LineageItem } from "@/types/copilot";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table";
import { cn } from "@/lib/utils";

interface CopilotAuditPanelProps {
  answer: CopilotAnswer | null;
  isOpen: boolean;
  onClose: () => void;
}

export function CopilotAuditPanel({ answer, isOpen, onClose }: CopilotAuditPanelProps) {
  const [activeTab, setActiveTab] = useState<"evidence" | "lineage" | "confidence">("evidence");

  if (!isOpen || !answer) return null;

  const unitNamesMap: Record<number, string> = {
    5555: "Casa Caiada (5555)",
    11495: "VIP (11495)",
    74014: "Real / Doze (74014)",
  };

  const formattedUnits = answer.units.map((u) => unitNamesMap[u] || `Unidade ${u}`).join(", ");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/75 backdrop-blur-sm transition-opacity animate-in fade-in duration-200">
      <div
        className="flex h-full w-full max-w-4xl flex-col bg-slate-950 border-l border-white/10 text-slate-100 shadow-2xl overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-labelledby="audit-panel-title"
      >
        {/* Header do Painel de Auditoria */}
        <div className="flex items-center justify-between border-b border-white/10 bg-slate-900/90 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="grid size-10 place-items-center rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <ShieldCheck size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 id="audit-panel-title" className="text-lg font-bold text-white tracking-tight">
                  Detalhamento de Auditoria Executiva
                </h2>
                <Badge variant="outline" className="bg-blue-500/10 text-blue-400 border-blue-500/20 text-[10px]">
                  Contrato Canônico
                </Badge>
              </div>
              <p className="text-xs text-slate-400">
                Linhagem de dados, matriz de evidências e integridade do especialista {answer.specialist}
              </p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="text-slate-400 hover:text-white hover:bg-white/10 rounded-lg"
          >
            <X size={20} />
          </Button>
        </div>

        {/* Banner de Verificação de Integridade */}
        <div className="bg-slate-900/50 border-b border-white/5 px-6 py-3 flex flex-wrap items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-2">
            <Building2 size={14} className="text-slate-400" />
            <span className="text-slate-400">Escopo Auditado:</span>
            <span className="font-semibold text-slate-200">{formattedUnits || "Consolidado 3 Unidades"}</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5 text-emerald-400">
              <CheckCircle2 size={14} />
              <span>webpostoWrites: {answer.webpostoWrites} (Somente Leitura)</span>
            </div>
            <div className="flex items-center gap-1.5 text-blue-400">
              <Lock size={14} />
              <span>Sanitização SDS: Ativa</span>
            </div>
          </div>
        </div>

        {/* Corpo do Painel com Abas */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Navegação de Abas Internas */}
          <div className="flex items-center gap-2 border-b border-white/10 pb-3">
            <button
              onClick={() => setActiveTab("evidence")}
              className={cn(
                "flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition",
                activeTab === "evidence"
                  ? "bg-blue-600 text-white shadow-lg shadow-blue-600/20"
                  : "bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-white border border-white/5"
              )}
            >
              <FileCheck2 size={15} />
              Evidências ({answer.evidence.length})
            </button>
            <button
              onClick={() => setActiveTab("lineage")}
              className={cn(
                "flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition",
                activeTab === "lineage"
                  ? "bg-blue-600 text-white shadow-lg shadow-blue-600/20"
                  : "bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-white border border-white/5"
              )}
            >
              <GitBranch size={15} />
              Linhagem de Dados ({answer.lineage.length})
            </button>
            <button
              onClick={() => setActiveTab("confidence")}
              className={cn(
                "flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition",
                activeTab === "confidence"
                  ? "bg-blue-600 text-white shadow-lg shadow-blue-600/20"
                  : "bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-white border border-white/5"
              )}
            >
              <ShieldCheck size={15} />
              Confiança & Regras ({answer.confidence.level})
            </button>
          </div>

          {/* ABA 1: EVIDÊNCIAS */}
          {activeTab === "evidence" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <FileCheck2 className="text-blue-400" size={16} />
                  Matriz de Evidências Auditadas
                </h3>
                <span className="text-xs text-slate-400">
                  {answer.evidence.length} {answer.evidence.length === 1 ? "evidência registrada" : "evidências registradas"}
                </span>
              </div>

              {answer.evidence.length === 0 ? (
                <Card className="border-slate-800 bg-slate-900/50">
                  <CardContent className="p-6 text-center text-slate-400 text-xs">
                    Nenhuma evidência direta anexada para esta resposta (Status: {answer.impact.status}).
                  </CardContent>
                </Card>
              ) : (
                <Card className="border-white/10 bg-slate-900/80 overflow-hidden">
                  <Table>
                    <TableHeader className="bg-slate-950/80">
                      <TableRow className="border-white/10">
                        <TableHead className="text-slate-400 text-xs">ID</TableHead>
                        <TableHead className="text-slate-400 text-xs">Fonte</TableHead>
                        <TableHead className="text-slate-400 text-xs">Resumo da Evidência</TableHead>
                        <TableHead className="text-slate-400 text-xs">Claim Status</TableHead>
                        <TableHead className="text-slate-400 text-xs">Unidade</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {answer.evidence.map((item: EvidenceItem) => (
                        <TableRow key={item.id} className="border-white/5 hover:bg-white/5 text-xs">
                          <TableCell className="font-mono text-blue-300 font-semibold">{item.id}</TableCell>
                          <TableCell className="font-medium text-slate-200">{item.fonte}</TableCell>
                          <TableCell className="text-slate-300 max-w-md">{item.resumo}</TableCell>
                          <TableCell>
                            <Badge
                              variant="outline"
                              className={cn(
                                "text-[10px]",
                                item.claimStatus === "FACT" && "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
                                item.claimStatus === "ESTIMATED" && "bg-amber-500/10 text-amber-400 border-amber-500/20",
                                item.claimStatus === "AUTO_CLASSIFIED" && "bg-blue-500/10 text-blue-400 border-blue-500/20",
                                item.claimStatus === "UNAVAILABLE" && "bg-slate-800 text-slate-400 border-slate-700",
                                item.claimStatus === "BLOCKED" && "bg-red-500/10 text-red-400 border-red-500/20"
                              )}
                            >
                              {item.claimStatus}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-slate-400">
                            {item.escopoConsolidado
                              ? "Consolidado (3 Filiais)"
                              : item.empresaCodigo
                              ? unitNamesMap[item.empresaCodigo] || `Filial ${item.empresaCodigo}`
                              : "N/A"}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </Card>
              )}
            </div>
          )}

          {/* ABA 2: LINHAGEM DE DADOS */}
          {activeTab === "lineage" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <GitBranch className="text-purple-400" size={16} />
                  Origem e Rastreabilidade do Dado
                </h3>
                <span className="text-xs text-slate-400">Rastreabilidade ponta a ponta</span>
              </div>

              {answer.lineage.length === 0 ? (
                <Card className="border-slate-800 bg-slate-900/50">
                  <CardContent className="p-6 text-center text-slate-400 text-xs">
                    Nenhum registro de linhagem anexado para esta resposta.
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-3">
                  {answer.lineage.map((item: LineageItem, idx: number) => (
                    <Card key={idx} className="border-white/10 bg-slate-900/80 p-4 space-y-3">
                      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/5 pb-2">
                        <div className="flex items-center gap-2">
                          <Database size={15} className="text-purple-400" />
                          <span className="font-semibold text-sm text-white">{item.fonte}</span>
                          <span className="text-xs text-slate-400">({item.origem})</span>
                        </div>
                        <Badge variant="outline" className="bg-purple-500/10 text-purple-300 border-purple-500/20 text-[10px]">
                          Natureza: {item.naturezaFonte}
                        </Badge>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                        <div>
                          <span className="block text-slate-500 font-medium">Referência:</span>
                          <span className="font-mono text-slate-300">{item.referencia}</span>
                        </div>
                        <div>
                          <span className="block text-slate-500 font-medium">Período de Extração:</span>
                          <span className="text-slate-300">
                            {item.periodo.inicio} a {item.periodo.fim}
                          </span>
                        </div>
                        <div>
                          <span className="block text-slate-500 font-medium">Status da Fonte:</span>
                          <span className="text-emerald-400 font-semibold">
                            {item.fonteLocal ? "Fonte Local Homologada" : "Remota"}
                          </span>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ABA 3: CONFIANÇA E REGRAS */}
          {activeTab === "confidence" && (
            <div className="space-y-4">
              <Card className="border-white/10 bg-slate-900/80 p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className={cn(
                        "grid size-12 place-items-center rounded-xl font-bold text-lg",
                        answer.confidence.level === "ALTA" && "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30",
                        answer.confidence.level === "MEDIA" && "bg-amber-500/20 text-amber-400 border border-amber-500/30",
                        answer.confidence.level === "BAIXA" && "bg-red-500/20 text-red-400 border border-red-500/30"
                      )}
                    >
                      {Math.round(answer.confidence.score * 100)}%
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold text-white">Score de Confiança Algorítmica</h4>
                      <p className="text-xs text-slate-400">
                        Nível de assertividade: <strong className="text-white">{answer.confidence.level}</strong>
                      </p>
                    </div>
                  </div>
                  <Badge variant="outline" className="bg-slate-800 text-slate-300 border-white/10">
                    Regra Canônica: {answer.impact.status}
                  </Badge>
                </div>

                <div className="space-y-2 border-t border-white/5 pt-3">
                  <h5 className="text-xs font-semibold text-slate-300">Justificativas do Algoritmo de Auditoria:</h5>
                  <ul className="space-y-1.5 text-xs text-slate-300">
                    {answer.confidence.reasons.map((reason: string, rIdx: number) => (
                      <li key={rIdx} className="flex items-start gap-2">
                        <CheckCircle2 size={14} className="text-blue-400 shrink-0 mt-0.5" />
                        <span>{reason}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </Card>

              {answer.probableCause && (
                <Card className="border-amber-500/20 bg-amber-500/5 p-4 text-xs text-amber-200 space-y-1">
                  <div className="font-semibold flex items-center gap-1.5">
                    <AlertTriangle size={14} className="text-amber-400" />
                    Causa Provável Identificada:
                  </div>
                  <p className="text-amber-100/90">{answer.probableCause}</p>
                </Card>
              )}
            </div>
          )}
        </div>

        {/* Rodapé com botão fechar */}
        <div className="border-t border-white/10 bg-slate-900/90 px-6 py-3 flex items-center justify-between">
          <span className="text-[11px] text-slate-500">
            Copiloto Executivo LOGOS • Proteção Anti-Alucinação Ativa
          </span>
          <Button size="sm" variant="secondary" onClick={onClose}>
            Concluir Auditoria
          </Button>
        </div>
      </div>
    </div>
  );
}
