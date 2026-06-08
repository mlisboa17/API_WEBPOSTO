import { APP_CONFIG } from "../config.js";
import { fetchEmpresasRede } from "../services/api.js";

/**
 * Stub para futura tela de selecao de Tenant / Empresa ativa.
 * Prepara o caminho para multi-empresa sem quebrar a UI atual que se baseia em filtro globais.
 */
export async function renderCompanySwitcher(container) {
  container.innerHTML = `
    <div class="company-switcher">
      <select id="tenantSelect" class="header-filter">
        <option value="">Carregando Empresas da Rede...</option>
      </select>
    </div>
  `;

  try {
    const apiResponse = await fetchEmpresasRede();
    const empresas = apiResponse?.resultados || [];

    const select = container.querySelector("#tenantSelect");
    if (!empresas.length) {
      select.innerHTML = '<option value="">(Nenhuma empresa vinculada)</option>';
      return;
    }

    const options = empresas.map(
      (e) => `<option value="${e.empresaCodigo}">${e.fantasia || e.razao} (${e.cnpj})</option>`
    );
    
    select.innerHTML = `
      <option value="">-- Mudar Empresa Ativa (Rede) --</option>
      ${options.join("")}
    `;

    select.addEventListener("change", (e) => {
      const codigo = e.target.value;
      if (codigo) {
        if (APP_CONFIG.debugWebPosto) {
          console.log(`[COMPANY SWITCHER] Empresa alterada para o codigo: ${codigo}`);
        }
        // Aqui conectara no state global ou forcaria o recarregamento dos filtros globais.
      }
    });
  } catch (err) {
    container.innerHTML = `<span class="small error" style="color:red;">Erro ao carregar tenants</span>`;
  }
}
