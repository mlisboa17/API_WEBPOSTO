import type {
  GrupoCadastro,
  PaginatedProdutos,
  Produto,
  ProdutoCrudResponse,
  ProdutoFormPayload,
  ProdutosQuery,
} from "@/types/produtos";

const API_BASE =
  typeof window === "undefined"
    ? process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8050"
    : "";

function pick<T>(obj: Record<string, unknown>, ...keys: string[]): T | undefined {
  for (const k of keys) {
    const v = obj[k];
    if (v !== undefined && v !== null && v !== "") return v as T;
  }
  return undefined;
}

export function produtoPrecoVenda(p: Produto): number {
  const v = pick<string | number>(p as unknown as Record<string, unknown>, "preco_venda", "precoVenda");
  return Number(v ?? 0);
}

export function produtoPrecoCusto(p: Produto): number {
  const v = pick<string | number>(p as unknown as Record<string, unknown>, "preco_custo", "precoCusto");
  return Number(v ?? 0);
}

export function produtoCodigoGrupo(p: Produto): number | undefined {
  const v = pick<number>(p as unknown as Record<string, unknown>, "codigo_grupo", "codigoGrupo");
  return v != null ? Number(v) : undefined;
}

export function produtoSubgrupos(p: Produto): number[] {
  const out: number[] = [];
  for (const k of [
    "sub_grupo_1_codigo",
    "subGrupo1Codigo",
    "sub_grupo_2_codigo",
    "subGrupo2Codigo",
    "sub_grupo_3_codigo",
    "subGrupo3Codigo",
  ]) {
    const v = (p as unknown as Record<string, unknown>)[k];
    if (v != null && v !== "") out.push(Number(v));
  }
  return [...new Set(out)];
}

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data.detail === "string") return data.detail;
    if (data.detail && typeof data.detail === "object") return JSON.stringify(data.detail);
    return data.mensagem || `Erro HTTP ${res.status}`;
  } catch {
    return `Erro HTTP ${res.status}`;
  }
}

interface ProxyV1Response {
  data?: {
    resultados?: Record<string, unknown>[];
  };
}

export async function fetchGruposCadastro(): Promise<GrupoCadastro[]> {
  const all: GrupoCadastro[] = [];

  try {
    const params = new URLSearchParams({
      pagina: "0",
      tamanhoPagina: "200",
    });
    const res = await fetch(`${API_BASE}/api/v1/proxy/GRUPO?${params}`, {
      cache: "no-store",
    });
    if (!res.ok) throw new Error(await parseError(res));

    const json: ProxyV1Response = await res.json();
    const rows = json.data?.resultados ?? [];

    for (const row of rows) {
      const cod = Number(row.grupoCodigo ?? row.codigo ?? 0);
      if (!cod) continue;
      all.push({
        codigo: cod,
        nome: String(row.nome ?? `Grupo ${cod}`),
        tipoGrupo: row.tipoGrupo ? String(row.tipoGrupo) : null,
      });
    }
  } catch (err) {
    console.error("Erro ao carregar grupos via proxy, tentando endpoint de backup", err);
    // Backup: tenta obter via grupos-produto
    try {
      const res = await fetch(`${API_BASE}/api/v1/webposto/grupos-produto`, {
        cache: "no-store",
      });
      if (res.ok) {
        const json = await res.json();
        const groups = json.grupos ?? [];
        for (const g of groups) {
          all.push({
            codigo: Number(g.codigo),
            nome: String(g.nome ?? `Grupo ${g.codigo}`),
            qtd_produtos: g.qtd_produtos,
          });
        }
      }
    } catch (fallbackErr) {
      console.error("Fallback de grupos falhou", fallbackErr);
    }
  }

  return all.sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
}

export async function fetchProdutos(query: ProdutosQuery): Promise<PaginatedProdutos> {
  const params = new URLSearchParams({
    pagina: String(query.pagina ?? 1),
    limite: String(query.limite ?? 30),
    situacao: query.situacao ?? "todos",
  });

  if (query.descricao?.trim()) params.set("descricao", query.descricao.trim());
  if (query.grupos?.length) params.set("grupos", query.grupos.join(","));
  if (query.subgrupos?.length) params.set("subgrupos", query.subgrupos.join(","));
  if (query.tipoProduto && query.tipoProduto !== "todos") {
    params.set("tipo_produto", query.tipoProduto);
  }

  const res = await fetch(`${API_BASE}/api/v1/webposto/produtos?${params}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function fetchProduto(id: number): Promise<Produto> {
  const res = await fetch(`${API_BASE}/api/v1/webposto/produtos/${id}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function createProduto(payload: ProdutoFormPayload): Promise<ProdutoCrudResponse> {
  const res = await fetch(`${API_BASE}/api/v1/webposto/produtos`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function updateProduto(
  id: number,
  payload: ProdutoFormPayload,
): Promise<ProdutoCrudResponse> {
  const res = await fetch(`${API_BASE}/api/v1/webposto/produtos/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}
