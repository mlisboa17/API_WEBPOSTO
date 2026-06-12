import type { ParsedStatementTransaction } from "@/types/statements";

function detectDelimiter(line: string): string {
  if (line.includes(";")) return ";";
  if (line.includes("\t")) return "\t";
  return ",";
}

function parseBrNumber(raw: string): number {
  const cleaned = raw.trim().replace(/[^\d,.-]/g, "");
  if (!cleaned) return NaN;
  if (cleaned.includes(",") && cleaned.includes(".")) {
    return Number.parseFloat(cleaned.replace(/\./g, "").replace(",", "."));
  }
  if (cleaned.includes(",")) {
    return Number.parseFloat(cleaned.replace(",", "."));
  }
  return Number.parseFloat(cleaned);
}

function normalizeDate(raw: string): string {
  const t = raw.trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(t)) return t;
  const br = t.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (br) return `${br[3]}-${br[2]}-${br[1]}`;
  return t.slice(0, 10);
}

export function parseCsvStatementContent(content: string): ParsedStatementTransaction[] {
  const lines = content
    .replace(/^\uFEFF/, "")
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);

  if (lines.length < 2) {
    throw new Error("CSV vazio ou sem linhas de dados.");
  }

  const delimiter = detectDelimiter(lines[0]);
  const headers = lines[0].split(delimiter).map((h) => h.trim().toLowerCase());

  const idxData = headers.findIndex((h) => /data|date|dt/.test(h));
  const idxDesc = headers.findIndex((h) => /desc|hist|memo|lan/.test(h));
  const idxValor = headers.findIndex((h) => /valor|amount|vlr|value/.test(h));

  if (idxData < 0 || idxValor < 0) {
    throw new Error("CSV deve conter colunas de data e valor reconhecíveis.");
  }

  const rows: ParsedStatementTransaction[] = [];
  for (let i = 1; i < lines.length; i += 1) {
    const cols = lines[i].split(delimiter);
    const data = normalizeDate(cols[idxData] ?? "");
    const valor = parseBrNumber(cols[idxValor] ?? "");
    const descricao = (idxDesc >= 0 ? cols[idxDesc] : cols[1])?.trim() || "Transação CSV";
    if (!data || !Number.isFinite(valor)) continue;
    rows.push({ id: `csv-${i}`, data, descricao, valor });
  }

  if (rows.length === 0) {
    throw new Error("Nenhuma linha válida encontrada no CSV.");
  }
  return rows;
}

export async function parseCsvStatementFile(file: File): Promise<ParsedStatementTransaction[]> {
  return parseCsvStatementContent(await file.text());
}
