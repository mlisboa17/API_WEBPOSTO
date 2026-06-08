import { APP_CONFIG } from "../config.js";
import { formatMissing } from "./formatters.js";

/**
 * Motor de Qualidade de Dados (Etapa 4 e 5).
 * Analisa a sujeira, rastreando chaves inexistentes baseados nos JSDocs de schema central.
 */
class DataQualityEngine {
  constructor() {
    this.totalRecords = 0;
    this.validRecords = 0;
    this.inconsistentRecords = 0;
    this.ignoredRecords = 0;
    this.inconsistencies = [];
  }

  reset() {
    this.totalRecords = 0;
    this.validRecords = 0;
    this.inconsistentRecords = 0;
    this.ignoredRecords = 0;
    this.inconsistencies = [];
  }

  evaluateSales(rows) {
    this.totalRecords += rows.length;
    rows.forEach(r => {
      let valid = true;
      if (!r.empresaCodigo) {
        valid = false;
        this.inconsistencies.push({ type: "warning", message: "Venda sem filial associada", ref: r.vendaCodigo });
      }
      if (valid) this.validRecords++;
      else this.inconsistentRecords++;
    });
  }

  evaluateExpenses(rows) {
    this.totalRecords += rows.length;
    rows.forEach(r => {
      let valid = true;
      if (!r.planoConta) {
        valid = false;
        this.inconsistencies.push({ type: "warning", message: "Despesa sem Plano de Conta", ref: formatMissing(r.valor) });
      }
      if (valid) this.validRecords++;
      else this.inconsistentRecords++;
    });
  }

  evaluateAccounts(rows) {
    this.totalRecords += rows.length;
    rows.forEach(r => {
      let valid = true;
      if (!r.status) {
        valid = false;
        this.inconsistencies.push({ type: "warning", message: "Conta sem categoria" });
      }
      if (valid) this.validRecords++;
      else this.inconsistentRecords++;
    });
  }

  getScore() {
    if (this.totalRecords === 0) return 100;
    return Math.floor((this.validRecords / this.totalRecords) * 100);
  }

  getReport() {
    return {
      score: this.getScore(),
      total: this.totalRecords,
      valids: this.validRecords,
      inconsistent: this.inconsistentRecords,
      ignored: this.ignoredRecords,
      logs: this.inconsistencies
    };
  }

  renderScorePanel(container) {
    const r = this.getReport();
    let colClass = "text-success";
    if (r.score < 95) colClass = "text-warning";
    if (r.score < 80) colClass = "text-danger";

    container.innerHTML = `
      <div class="panel score-panel">
        <h3>Qualidade dos Dados</h3>
        <div class="score-val ${colClass}">${r.score}%</div>
        <div class="score-details small">
          <div>Registros válidos: ${r.valids}</div>
          <div>Inconsistentes: ${r.inconsistent}</div>
          <div>Ignorados: ${r.ignored}</div>
        </div>
      </div>
    `;
  }
}

export const dataQualityEngine = new DataQualityEngine();
