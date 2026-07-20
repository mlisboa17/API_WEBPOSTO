export const LICENSED_COMPANIES = Object.freeze([
  { empresaCodigo: "11495", nome: "POSTO VIP" },
  { empresaCodigo: "5555", nome: "AP CASA CAIADA" },
  { empresaCodigo: "74014", nome: "POSTO DOZE FILIAL II" },
]);

export const LICENSED_COMPANY_CODES = new Set(LICENSED_COMPANIES.map((item) => item.empresaCodigo));

export const MANAGEMENT_DEPARTMENTS = Object.freeze([
  { id: "combustiveis", label: "Combustíveis" },
  { id: "conveniencia", label: "Conveniência" },
  { id: "lubrificantes", label: "Lubrificantes" },
]);

// Mapa confirmado em /INTEGRACAO/GRUPO nas três licenças em 17/07/2026.
export const WEBPOSTO_GROUP_DEPARTMENT_MAP = Object.freeze({
  "24554": "combustiveis",
  "24555": "lubrificantes",
  "24556": "lubrificantes",
  "24557": "lubrificantes",
  "28811": "lubrificantes",
  "62009": "lubrificantes",
  "162956": "conveniencia",
  "162989": "conveniencia",
  "51350": "conveniencia",
  "55443": "conveniencia",
  "55444": "conveniencia",
  "55445": "conveniencia",
  "55446": "conveniencia",
  "55447": "conveniencia",
  "55449": "conveniencia",
  "55450": "conveniencia",
  "55451": "conveniencia",
  "55452": "conveniencia",
  "55453": "conveniencia",
  "56795": "conveniencia",
});

export const UNMAPPED_WEBPOSTO_GROUP_CODES = new Set(["25016", "26039", "29273"]);

export function isLicensedCompanyCode(value) {
  return LICENSED_COMPANY_CODES.has(String(value ?? ""));
}
