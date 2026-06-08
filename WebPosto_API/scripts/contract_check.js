const fs = require('fs');
const path = require('path');

const openapiPath = path.join(__dirname, '..', 'openapi_specs.json');

if (!fs.existsSync(openapiPath)) {
  console.error("❌ Arquivo openapi_specs.json não encontrado. Gere ele primeiro rodando o servidor e buscando de /openapi.json");
  process.exit(1);
}

const spec = JSON.parse(fs.readFileSync(openapiPath, 'utf8'));

// Lista de rotas ativamente chamadas pela UI via fetchWebPosto / api.js frontend
const FRONTEND_ENDPOINTS = [
  "/v1/financial/companies",
  "/v1/financial/expenses",
  "/v1/sales",
  "/v1/stock",
  "/v1/financial/accounts-payable"
];

console.log("=== INICIANDO VALIDACAO DE CONTRATO (OPENAPI) ===");

let hasWarning = false;

FRONTEND_ENDPOINTS.forEach(endpoint => {
  const pathObj = spec.paths[endpoint];
  if (!pathObj) {
    console.warn(`[WARNING] O endpoint "${endpoint}" é consumido pelo frontend mas NAO foi encontrado na OpenAPI atual.`);
    hasWarning = true;
    return;
  }
  
  if (!pathObj.get) {
    console.warn(`[WARNING] O endpoint "${endpoint}" não declarou GET na especificação, mas o frontend utiliza o método GET.`);
    hasWarning = true;
    return;
  }
  
  console.log(`[OK] O endpoint frontend "${endpoint}" mapeado com sucesso na especificação.`);
});

console.log("\n=== VALIDACAO DE SCHEMA ===");
// Simplificamos a validações apenas listando esquemas
const schemas = Object.keys(spec.components?.schemas || {});
if (schemas.length === 0) {
  console.warn("[WARNING] Nenhum schema Pydantic exposto profundamente na documentacao (tipagem vindo solta com dict). " + 
               "Considere adicionar respostas tipadas (Pydantic models) nas rotas de integração WebPosto para aproveitar geração 100% tipada.");
  hasWarning = true;
} else {
  console.log(`[OK] Schemas detectados: ${schemas.join(", ")}`);
}

if (!hasWarning) {
  console.log("\n✅ Contrato da API validado com sucesso! Nenhuma quebra detectada.");
} else {
  console.log("\n⚠ Alertas no contrato detectados. O frontend pode precisar de tratamento de nulos/undefined se as assinaturas divergirem.");
}
