"use client";

import { useState, useEffect, useCallback } from "react";
import { ReviewableFact } from "@/types/api";
import { apiService } from "@/lib/api";
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { RefreshCcw, Check, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface ExpenseClassificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  start: string;
  end: string;
}

export function ExpenseClassificationModal({ isOpen, onClose, start, end }: ExpenseClassificationModalProps) {
  const [facts, setFacts] = useState<ReviewableFact[]>([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState<string | null>(null);

  const fetchFacts = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiService.getReviewableFacts(start, end);
      setFacts(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [start, end]);

  useEffect(() => {
    (async () => {
      if (isOpen) await fetchFacts();
    })();
  }, [isOpen, fetchFacts]);

  const handleClassify = async (factId: string, department: string) => {
    try {
      setProcessing(factId);
      await apiService.classifyExpense(factId, department, "Diretoria", "Classificado via Cockpit");
      setFacts(prev => prev.filter(f => f.factId !== factId));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro ao classificar";
      alert("Erro ao classificar: " + message);
    } finally {
      setProcessing(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-white/10 rounded-xl shadow-2xl w-full max-w-6xl max-h-[90vh] flex flex-col">
        <div className="p-6 border-b border-white/5 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white">Conciliação de Despesas</h2>
            <p className="text-sm text-slate-400">Classifique as despesas pendentes para liberar a DRE</p>
          </div>
          <div className="flex items-center gap-3">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={fetchFacts} 
              disabled={loading}
              className="bg-cyan-500/10 border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20 hover:text-cyan-200"
            >
              <RefreshCcw size={14} className={cn("text-cyan-400", loading && "animate-spin")} />
            </Button>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X size={20} />
            </Button>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 gap-4">
              <RefreshCcw className="animate-spin text-cyan-400" size={32} />
              <p className="text-slate-400">Buscando pendências na API...</p>
            </div>
          ) : facts.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 gap-2">
              <Check className="text-green-500" size={48} />
              <p className="text-xl font-medium text-white">Tudo conciliado!</p>
              <p className="text-slate-400">Não há despesas pendentes para este período.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-white/5 hover:bg-transparent">
                  <TableHead>Data</TableHead>
                  <TableHead>Unidade</TableHead>
                  <TableHead>Descrição</TableHead>
                  <TableHead>Fornecedor</TableHead>
                  <TableHead className="text-right">Valor</TableHead>
                  <TableHead className="text-center">Departamento Alvo</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {facts.map((fact) => (
                  <TableRow key={fact.factId} className="border-white/5">
                    <TableCell className="text-xs">{new Date(fact.date).toLocaleDateString()}</TableCell>
                    <TableCell className="text-xs font-bold">{fact.companyName}</TableCell>
                    <TableCell className="text-xs max-w-xs truncate font-medium">{fact.description}</TableCell>
                    <TableCell className="text-xs text-slate-400">{fact.supplier || "—"}</TableCell>
                    <TableCell className="text-right text-xs font-mono font-bold">
                      {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(fact.amount)}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center justify-center gap-1">
                        <Button 
                          size="sm" 
                          variant="outline" 
                          className="text-[10px] h-7 px-2 hover:bg-blue-500/20 border-blue-500/20"
                          onClick={() => handleClassify(fact.factId, "combustiveis")}
                          disabled={!!processing}
                        >
                          Pista
                        </Button>
                        <Button 
                          size="sm" 
                          variant="outline" 
                          className="text-[10px] h-7 px-2 hover:bg-orange-500/20 border-orange-500/20"
                          onClick={() => handleClassify(fact.factId, "conveniencia")}
                          disabled={!!processing}
                        >
                          Loja
                        </Button>
                        <Button 
                          size="sm" 
                          variant="outline" 
                          className="text-[10px] h-7 px-2 hover:bg-purple-500/20 border-purple-500/20"
                          onClick={() => handleClassify(fact.factId, "lubrificantes")}
                          disabled={!!processing}
                        >
                          Lub
                        </Button>
                        <Button 
                          size="sm" 
                          variant="outline" 
                          className="text-[10px] h-7 px-2 hover:bg-slate-500/20 border-slate-500/20"
                          onClick={() => handleClassify(fact.factId, "administrativo")}
                          disabled={!!processing}
                        >
                          Adm
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </div>
    </div>
  );
}
