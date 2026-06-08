const STORAGE_KEY = "logos-space-product-catalog-v1";
const TTL_MS = 24 * 60 * 60 * 1000;

let memoryCatalog = null;
let memoryLoadedAt = 0;

function nowMs() {
  return Date.now();
}

function isCodeLike(text) {
  const value = String(text || "").trim();
  if (!value) return true;
  if (/^(none|null|undefined|todos|all)$/i.test(value)) return true;
  return /^produto\s+\d+$/i.test(value) || /^\d+$/.test(value);
}

function buildMap(products = []) {
  const map = new Map();
  products.forEach((item) => {
    const code = Number(item?.produtoCodigo);
    if (!Number.isFinite(code)) return;
    map.set(code, item);
  });
  return map;
}

function readStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || !Array.isArray(parsed.products)) return null;
    if ((parsed.loadedAt || 0) + TTL_MS < nowMs()) return null;
    return parsed;
  } catch {
    return null;
  }
}

function writeStorage(products) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ loadedAt: nowMs(), products }));
  } catch {}
}

export async function ensureProductCatalog(fetcher, companyCodes = []) {
  if (memoryCatalog && memoryLoadedAt + TTL_MS > nowMs()) {
    return memoryCatalog;
  }

  const cached = readStorage();
  if (cached) {
    memoryCatalog = buildMap(cached.products);
    memoryLoadedAt = cached.loadedAt;
    return memoryCatalog;
  }

  const payload = await fetcher(companyCodes);
  const products = Array.isArray(payload?.products) ? payload.products : [];
  memoryCatalog = buildMap(products);
  memoryLoadedAt = nowMs();
  writeStorage(products);
  return memoryCatalog;
}

export function resolveProduct(productCatalog, productCode, fallbackName = "") {
  const code = Number(productCode);
  const hasCode = Number.isFinite(code);
  const known = hasCode ? productCatalog?.get(code) : null;
  const knownName = String(known?.nomeProduto || "").trim();
  const fallback = String(fallbackName || "").trim();

  if (knownName && !isCodeLike(knownName)) {
    return {
      produtoCodigo: hasCode ? code : productCode,
      label: knownName,
      known: true,
      grupoProduto: known?.grupoProduto || "",
      tipoProduto: known?.tipoProduto || "",
      combustivel: !!known?.combustivel,
      badge: "",
    };
  }

  if (fallback && !isCodeLike(fallback)) {
    return {
      produtoCodigo: hasCode ? code : productCode,
      label: fallback,
      known: true,
      grupoProduto: known?.grupoProduto || "",
      tipoProduto: known?.tipoProduto || "",
      combustivel: !!known?.combustivel,
      badge: "",
    };
  }

  const codeLabel = hasCode ? String(code) : String(productCode || fallback || "Sem código");
  return {
    produtoCodigo: hasCode ? code : productCode,
    label: `${codeLabel} — Produto não cadastrado`,
    known: false,
    grupoProduto: known?.grupoProduto || "",
    tipoProduto: known?.tipoProduto || "",
    combustivel: !!known?.combustivel,
    badge: "não cadastrado",
  };
}

export function enrichFuelSummary(productCatalog, items = []) {
  return (items || []).map((item) => {
    const resolved = resolveProduct(productCatalog, item?.produtoCodigo, item?.combustivel);
    return {
      ...item,
      combustivelDisplay: resolved.label,
      produtoNaoCadastrado: !resolved.known,
      grupoProduto: item?.grupoProduto || resolved.grupoProduto,
      tipoProduto: item?.tipoProduto || resolved.tipoProduto,
    };
  });
}

export function enrichFuelExecutive(productCatalog, payload = null) {
  if (!payload) return payload;
  const combustiveis = enrichFuelSummary(productCatalog, payload.combustiveis || []);
  const details = (payload.detalhes || []).map((item) => {
    const resolved = resolveProduct(productCatalog, item?.produtoCodigo, item?.combustivel);
    return {
      ...item,
      combustivelDisplay: resolved.label,
      produtoNaoCadastrado: !resolved.known,
      grupoProduto: resolved.grupoProduto,
      tipoProduto: resolved.tipoProduto,
    };
  });
  const lider = payload?.kpis?.combustivelLider || {};
  const liderResolved = resolveProduct(productCatalog, lider?.produtoCodigo, lider?.nome);
  return {
    ...payload,
    combustiveis,
    detalhes: details,
    kpis: {
      ...(payload.kpis || {}),
      combustivelLider: {
        ...lider,
        nome: liderResolved.label,
      },
    },
  };
}

export function enrichStockRows(productCatalog, rows = []) {
  return (rows || []).map((row) => {
    const resolved = resolveProduct(productCatalog, row?.codigo, row?.descricao);
    return {
      ...row,
      descricaoDisplay: row?.tipoRegistro === "produto" || row?.tipoRegistro === "estoque_periodo"
        ? resolved.label
        : (row?.descricao || resolved.label),
      produtoNaoCadastrado: !resolved.known && (row?.tipoRegistro === "produto" || row?.tipoRegistro === "estoque_periodo"),
      grupoProduto: resolved.grupoProduto,
      tipoProduto: resolved.tipoProduto,
    };
  });
}
