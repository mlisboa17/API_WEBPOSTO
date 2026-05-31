import { fuelLabel, isAfericao, rowLitros, rowValor } from "@/lib/fuel-catalog";
import { formatDateBR, presetRange } from "@/lib/datetime-br";

export { formatDateBR, presetRange };

export interface AbastecimentoRow {
  dataFiscal?: string;
  horaFiscal?: string;
  codigoBico?: number | string;
  codigoProduto?: number | string;
  nomeProduto?: string;
  quantidade?: number;
  valorUnitario?: number;
  valorTotal?: number;
  afericao?: boolean | number | string;
  [key: string]: unknown;
}

export interface FuelSummary {
  codigo: string;
  nome: string;
  litros: number;
  valor: number;
  qtd: number;
}

export interface AbastecimentoResumo {
  totalLitros: number;
  totalValor: number;
  totalRegistros: number;
  porCombustivel: FuelSummary[];
  registros: AbastecimentoRow[];
}

export function aggregateAbastecimentos(
  rows: AbastecimentoRow[],
  { excluirAfericao = true }: { excluirAfericao?: boolean } = {},
): AbastecimentoResumo {
  const filtered = excluirAfericao
    ? rows.filter((r) => !isAfericao(r as Record<string, unknown>))
    : rows;

  const porCodigo = new Map<string, FuelSummary>();

  for (const row of filtered) {
    const cod = String(row.codigoProduto ?? row.produtoCodigo ?? "");
    const nome = fuelLabel(cod, row.nomeProduto as string | undefined);
    const litros = rowLitros(row as Record<string, unknown>);
    const valor = rowValor(row as Record<string, unknown>);

    const cur = porCodigo.get(cod) ?? { codigo: cod, nome, litros: 0, valor: 0, qtd: 0 };
    cur.litros += litros;
    cur.valor += valor;
    cur.qtd += 1;
    porCodigo.set(cod, cur);
  }

  const porCombustivel = [...porCodigo.values()].sort((a, b) => b.litros - a.litros);
  const totalLitros = porCombustivel.reduce((s, x) => s + x.litros, 0);
  const totalValor = porCombustivel.reduce((s, x) => s + x.valor, 0);

  return {
    totalLitros,
    totalValor,
    totalRegistros: filtered.length,
    porCombustivel,
    registros: filtered,
  };
}
