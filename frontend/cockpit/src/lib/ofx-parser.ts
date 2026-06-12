import type { ParsedStatementTransaction } from "@/types/statements";

function parseOfxDate(raw: string): string {
  const digits = raw.replace(/\D/g, "").slice(0, 8);
  if (digits.length !== 8) return "";
  return `${digits.slice(0, 4)}-${digits.slice(4, 6)}-${digits.slice(6, 8)}`;
}

function readTag(block: string, tag: string): string {
  const re = new RegExp(`<${tag}>([^<\\n\\r]+)`, "i");
  const match = block.match(re);
  return match?.[1]?.trim() ?? "";
}

/**
 * Parser OFX 1.x (SGML) — extrai STMTTRN do arquivo.
 */
export function parseOfxContent(content: string): ParsedStatementTransaction[] {
  const normalized = content.replace(/\r\n/g, "\n");
  const blocks = normalized.split(/<STMTTRN>/i).slice(1);
  const out: ParsedStatementTransaction[] = [];

  blocks.forEach((chunk, index) => {
    const block = chunk.split(/<\/STMTTRN>/i)[0] ?? chunk;
    const valor = Number.parseFloat(readTag(block, "TRNAMT").replace(",", "."));
    const data = parseOfxDate(readTag(block, "DTPOSTED") || readTag(block, "DTUSER"));
    const descricao =
      readTag(block, "MEMO") ||
      readTag(block, "NAME") ||
      readTag(block, "CHECKNUM") ||
      "Transação OFX";
    const fitid = readTag(block, "FITID");
    const tipo = readTag(block, "TRNTYPE");

    if (!Number.isFinite(valor) || !data) return;

    out.push({
      id: fitid || `ofx-${index + 1}`,
      data,
      descricao,
      valor,
      tipo,
    });
  });

  return out;
}

export async function parseOfxFile(file: File): Promise<ParsedStatementTransaction[]> {
  const text = await file.text();
  const rows = parseOfxContent(text);
  if (rows.length === 0) {
    throw new Error("Nenhuma transação STMTTRN encontrada no arquivo OFX.");
  }
  return rows;
}
