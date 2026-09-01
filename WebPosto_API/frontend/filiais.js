import { normalizeEmpresaRede } from "./services/api.js";
import { isLicensedCompanyCode } from "./config/managementScope.js";

const FALLBACK_FILIAIS = [
  { nro: 1, codWeb: 11495, razaoSocial: "RIO DOCE COMERCIO E SERVICOS LTDA", nomeFantasia: "POSTO VIP", cnpj: "03.008.754/0001-86", ativo: true, cidade: "OLINDA", uf: "PE", tipoFilial: "Posto", status: "CONFIRMADA" },
  { nro: 2, codWeb: 5555, razaoSocial: "AUTO POSTO CASA CAIADA LTDA", nomeFantasia: "AP CASA CAIADA", cnpj: "04.284.939/0001-86", ativo: true, cidade: "OLINDA", uf: "PE", tipoFilial: "Posto", status: "CONFIRMADA" },
  { nro: 3, codWeb: 5256, razaoSocial: "DISTRIBUIDORA RS DERIVADOS DE PETROLEO LTDA", nomeFantasia: "POSTO BR SHOPPING", cnpj: "07.018.760/0001-75", ativo: true, cidade: "OLINDA", uf: "PE", tipoFilial: "Posto", status: "CONFIRMADA" },
  { nro: 4, codWeb: 5333, razaoSocial: "POSTO CIDADE PATRIMONIO LTDA", nomeFantasia: "POSTO JANGA", cnpj: "05.428.059/0002-80", ativo: true, cidade: "PAULISTA", uf: "PE", tipoFilial: "Posto", status: "CONFIRMADA" },
  { nro: 5, codWeb: 5556, razaoSocial: "POSTO CIDADE PATRIMONIO LTDA", nomeFantasia: "POSTO CIDADE PATRIMONIO", cnpj: "05.428.059/0001-07", ativo: true, cidade: "OLINDA", uf: "PE", tipoFilial: "Posto", status: "CONFIRMADA" },
  { nro: 6, codWeb: 5557, razaoSocial: "POSTO ENSEADA DO NORTE LTDA", nomeFantasia: "POSTO ENSEADA DO NORTE", cnpj: "00.338.804/0001-03", ativo: true, cidade: "OLINDA", uf: "PE", tipoFilial: "Posto", status: "CONFIRMADA" },
  { nro: 7, codWeb: 5558, razaoSocial: "REAL RECIFE LTDA", nomeFantasia: "POSTO REAL", cnpj: "24.156.978/0001-05", ativo: false, cidade: "ABREU E LIMA", uf: "PE", tipoFilial: "Posto", status: "INATIVA", dataEncerramento: "2026-05-20" },
  { nro: 8, codWeb: 5559, razaoSocial: "RJ COMBUSTIVEIS E LUBRIFICANTES", nomeFantasia: "POSTO RJ", cnpj: "08.726.064/0001-86", ativo: true, cidade: "OLINDA", uf: "PE", tipoFilial: "Posto", status: "CONFIRMADA" },
  { nro: 9, codWeb: null, razaoSocial: "AUTO POSTO GLOBO LTDA", nomeFantasia: "AUTO POSTO GLOBO", cnpj: "41.043.647/0001-88", ativo: false, cidade: "OLINDA", uf: "PE", tipoFilial: "Posto", status: "PENDENTE_IDENTIFICACAO" },
  { nro: 10, codWeb: 5560, razaoSocial: "AUTO POSTO IGARASSU LTDA", nomeFantasia: "POSTO SERTÃ", cnpj: "04.274.378/0001-34", ativo: true, cidade: "IGARASSU", uf: "PE", tipoFilial: "Posto", status: "CONFIRMADA" },
  { nro: 11, codWeb: 46433, razaoSocial: "POSTO DOZE COMERCIO DE COMBUSTIVEIS E DERIVADOS DE PETROLEO", nomeFantasia: "POSTO DOZE", cnpj: "52.308.604/0001-01", ativo: true, cidade: "OLINDA", uf: "PE", tipoFilial: "Posto", status: "CONFIRMADA" },
  { nro: 12, codWeb: 74014, razaoSocial: "POSTO DOZE COMERCIO DE COMBUSTIVEIS E DERIVADOS DE PETROLEO", nomeFantasia: "POSTO DOZE FILIAL II", cnpj: "52.308.604/0002-84", ativo: true, cidade: "ABREU E LIMA", uf: "PE", tipoFilial: "Posto", status: "CONFIRMADA" },
];

const FILIAL_UI_EXTRAS = {
  "11495": { nro: 1, cidade: "OLINDA", uf: "PE", tipoFilial: "Posto" },
  "5555": { nro: 2, cidade: "OLINDA", uf: "PE", tipoFilial: "Posto" },
  "5256": { nro: 3, cidade: "OLINDA", uf: "PE", tipoFilial: "Posto" },
  "5333": { nro: 4, cidade: "PAULISTA", uf: "PE", tipoFilial: "Posto" },
  "5556": { nro: 5, cidade: "OLINDA", uf: "PE", tipoFilial: "Posto" },
  "5557": { nro: 6, cidade: "OLINDA", uf: "PE", tipoFilial: "Posto" },
  "5558": { nro: 7, cidade: "ABREU E LIMA", uf: "PE", tipoFilial: "Posto" },
  "5559": { nro: 8, cidade: "OLINDA", uf: "PE", tipoFilial: "Posto" },
  "5560": { nro: 10, cidade: "IGARASSU", uf: "PE", tipoFilial: "Posto" },
  "46433": { nro: 11, cidade: "OLINDA", uf: "PE", tipoFilial: "Posto" },
  "74014": { nro: 12, cidade: "ABREU E LIMA", uf: "PE", tipoFilial: "Posto" },
};

function enrichUiExtras(row) {
  const key = row.codWeb != null && row.codWeb !== "" ? String(row.codWeb) : null;
  const extra = key ? FILIAL_UI_EXTRAS[key] : null;
  return extra ? { ...row, ...extra, tipoFilial: row.tipoFilial || extra.tipoFilial || "Posto" } : row;
}

function isFilialComprovada(filial) {
  if (filial?.comprovada === true) return true;
  if (filial?.comprovada === false) return false;
  const status = String(filial?.statusEvidencia || filial?.status || "").toUpperCase();
  if (status === "PENDENTE_EVIDENCIA" || status === "PENDENTE_IDENTIFICACAO") return false;
  return status === "COMPROVADA" || status === "CONFIRMADA" || status === "INATIVA";
}

function mapManifestRows(rows = []) {
  if (!rows?.length) {
    return FALLBACK_FILIAIS.filter(isFilialComprovada).filter((row) => isLicensedCompanyCode(row.codWeb)).map((row) => ({
      ...row,
      statusEvidencia: row.status === "INATIVA" ? "COMPROVADA" : row.status === "CONFIRMADA" ? "COMPROVADA" : row.status,
      comprovada: true,
      origem: "fallback",
    }));
  }
  return rows
    .map((row) => enrichUiExtras({
      nro: row.nro ?? null,
      codWeb: row.codWeb ?? (row.empresaCodigo && /^\d+$/.test(String(row.empresaCodigo)) ? Number(row.empresaCodigo) : null),
      razaoSocial: row.razaoSocial || "",
      nomeFantasia: row.nomeFantasia || "",
      cnpj: row.cnpj || null,
      ativo: Boolean(row.ativo ?? row.ativa),
      cidade: row.cidade || null,
      uf: row.uf || null,
      tipoFilial: row.tipoFilial || "Posto",
      status: row.statusEvidencia || row.status || "COMPROVADA",
      statusEvidencia: row.statusEvidencia || row.status || "COMPROVADA",
      comprovada: isFilialComprovada(row),
      dataEncerramento: row.dataEncerramento || null,
      origem: "manifest",
    }))
    .filter((row) => row.comprovada && isLicensedCompanyCode(row.codWeb));
}

async function loadFiliaisBase() {
  try {
    const response = await fetch(new URL("./data/filiais.json", import.meta.url));
    if (!response.ok) return mapManifestRows();
    const manifest = await response.json();
    const rows = manifest.filiais;
    return mapManifestRows(rows);
  } catch (_error) {
    return mapManifestRows();
  }
}

export const FILIAIS = await loadFiliaisBase();

let FILIAIS_REDE = FILIAIS.map((filial) => ({ ...filial, origem: filial.origem || "local" }));
let FILIAIS_POR_CNPJ = new Map();
const CODIGO_EMPRESA_PARA_CNPJ = new Map();
let FILIAIS_POR_CODWEB = new Map();

function rebuildIndexes() {
  FILIAIS_POR_CNPJ = new Map(
    FILIAIS_REDE.filter((filial) => filial?.cnpj).map((filial) => [String(filial.cnpj).replace(/\D/g, ""), filial])
  );
  FILIAIS_POR_CODWEB = new Map(
    FILIAIS_REDE
      .filter((filial) => filial.codWeb !== null && filial.codWeb !== undefined && filial.codWeb !== "")
      .map((filial) => [String(filial.codWeb), filial])
  );
}

function filialMapKey(filial) {
  if (filial?.codWeb !== null && filial?.codWeb !== undefined && filial?.codWeb !== "") {
    return String(filial.codWeb);
  }
  return String(filial?.cnpj || "").replace(/\D/g, "");
}

rebuildIndexes();

function normalizeText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toUpperCase();
}

function getFilialByNome(nome) {
  const normalized = normalizeText(nome);
  if (!normalized) return null;
  return (
    FILIAIS.find(
      (filial) =>
        normalizeText(filial.nomeFantasia) === normalized || normalizeText(filial.razaoSocial) === normalized
    ) || null
  );
}

export function hydrateFiliaisCodigoMap(empresas = []) {
  empresas.forEach((empresa) => {
    const codigo = empresa?.empresaCodigo ?? empresa?.codWeb;
    if (codigo === null || codigo === undefined || codigo === "") return;

    const cnpjRaw = String(empresa?.cnpj || "").replace(/\D/g, "");
    if (cnpjRaw && FILIAIS_POR_CNPJ.has(cnpjRaw)) {
      CODIGO_EMPRESA_PARA_CNPJ.set(String(codigo), cnpjRaw);
      return;
    }

    const porNome = getFilialByNome(
      empresa?.nome || empresa?.nomeFantasia || empresa?.fantasia || empresa?.razao || empresa?.razaoSocial
    );
    if (porNome) {
      CODIGO_EMPRESA_PARA_CNPJ.set(String(codigo), String(porNome.cnpj).replace(/\D/g, ""));
    }
  });
}

export function mergeFiliais(apiFiliais = []) {
  const locais = FILIAIS;
  const normalizadas = apiFiliais
    .map((row) => normalizeEmpresaRede(row))
    .filter((filial) => filialMapKey(filial) && isLicensedCompanyCode(filial.codWeb));

  const mapa = new Map();
  for (const filial of locais) {
    mapa.set(filialMapKey(filial), { ...filial, origem: filial.origem || "local" });
  }
  for (const filial of normalizadas) {
    const key = filialMapKey(filial);
    mapa.set(key, { ...mapa.get(key), ...filial, origem: "api" });
  }

  FILIAIS_REDE = Array.from(mapa.values());
  rebuildIndexes();
  return FILIAIS_REDE;
}

export function getFiliaisAtivas() {
  return FILIAIS_REDE.filter((filial) => filial.ativo && isFilialComprovada(filial));
}

export function getFiliaisBaseCodWebSet() {
  return new Set(
    FILIAIS.map((filial) => filial?.codWeb)
      .filter((codWeb) => codWeb !== null && codWeb !== undefined && codWeb !== "")
      .map((codWeb) => String(codWeb))
  );
}

function limparCnpj(cnpj) {
  return String(cnpj || "").replace(/\D/g, "");
}

export function getFilialByCodWeb(codWeb) {
  if (codWeb === null || codWeb === undefined || codWeb === "") return null;
  return FILIAIS_POR_CODWEB.get(String(codWeb)) || null;
}

export function getFilialByCnpj(cnpj) {
  if (!cnpj) return null;
  return FILIAIS_POR_CNPJ.get(limparCnpj(cnpj)) || null;
}

export function getFilialByNro(nro) {
  return FILIAIS.find((filial) => Number(filial.nro) === Number(nro)) || null;
}

export function getNomeFilial(valor) {
  if (!valor) return "";
  const porCodWeb = getFilialByCodWeb(valor);
  if (porCodWeb) return porCodWeb.nomeFantasia;
  const porCnpj = getFilialByCnpj(valor);
  if (porCnpj) return porCnpj.nomeFantasia;
  const porNro = getFilialByNro(valor);
  if (porNro) return porNro.nomeFantasia;
  const cnpjPorCodigo = CODIGO_EMPRESA_PARA_CNPJ.get(String(valor));
  if (cnpjPorCodigo) {
    const porCodigoMapeado = getFilialByCnpj(cnpjPorCodigo);
    if (porCodigoMapeado) return porCodigoMapeado.nomeFantasia;
  }
  const porNome = getFilialByNome(valor);
  if (porNome) return porNome.nomeFantasia;
  return String(valor);
}

export function resolveFilialFromRow(row = {}) {
  const candidates = [
    row.codWeb,
    row.codigoWeb,
    row.empresaCodigo,
    row.filialCodigo,
    row.cnpj,
    row.empresaCnpj,
    row.cnpjEmpresa,
    row.filialCnpj,
    row.filial,
    row.empresa,
    row.nome,
    row.nomeFantasia,
  ];
  let fallback = "";
  for (const value of candidates) {
    if (value === null || value === undefined || value === "") continue;
    const resolved = getNomeFilial(value);
    if (resolved !== String(value)) return resolved;
    if (!fallback) fallback = resolved;
  }
  return fallback;
}

export function getFiliaisOptions() {
  return FILIAIS_REDE.map((filial) => ({
    value: filial.codWeb || filial.cnpj,
    label: filial.nomeFantasia,
    cnpj: filial.cnpj,
    nro: filial.nro,
    codWeb: filial.codWeb,
    origem: filial.origem,
  }));
}
