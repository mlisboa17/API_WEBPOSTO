import { getCachedAnalytics } from "./analyticsCache.js";

function parseNum(val) {
  if (val === null || val === undefined) return 0;
  const num = Number(String(val).replace(/\s/g, "").replace(/R\$/g, "").replace(/\./g, "").replace(/,/g, "."));
  return isNaN(num) ? 0 : num;
}

export function computeIndicators(sales = [], expenses = []) {
  // Usa o tamanho dos arrays como hash basico/rapido para o cache
  const key = `indicators_${sales.length}_${expenses.length}`;
  return getCachedAnalytics(key, () => {
    let faturamento = 0;
    let qtdVendas = 0;
    const clientesSet = new Set();

    sales.forEach(v => {
      faturamento += parseNum(v.totalVenda);
      qtdVendas += 1;
      if (v.cliente && String(v.cliente).trim() !== "") {
        clientesSet.add(v.cliente);
      }
    });

    let despesasTotais = 0;
    expenses.forEach(e => {
      despesasTotais += parseNum(e.valor);
    });

    const resultado = faturamento - despesasTotais;
    const ticketMedio = qtdVendas > 0 ? faturamento / qtdVendas : 0;

    return {
      faturamento,
      despesasTotais,
      resultado,
      ticketMedio,
      qtdVendas,
      qtdClientes: clientesSet.size,
    };
  });
}

export function computeStockIndicator(stock = []) {
  const key = `stock_${stock.length}`;
  return getCachedAnalytics(key, () => {
    let estoqueTotal = 0;
    stock.forEach(s => {
      estoqueTotal += parseNum(s.quantidade);
    });
    return { estoqueTotal };
  });
}

export function computeDRE(sales = [], expenses = []) {
  const key = `dre_${sales.length}_${expenses.length}`;
  return getCachedAnalytics(key, () => {
    let receitas = 0;
    sales.forEach(v => receitas += parseNum(v.totalVenda));
    
    let custosProduto = 0;
    let outrasDespesas = 0;

    expenses.forEach(e => {
      const valor = parseNum(e.valor);
      const tipo = String(e.tipoDespesa || "").toLowerCase();
      // Classificacao basica (custo vs despesa)
      if (tipo.includes("custo") || tipo.includes("fornecedor")) {
        custosProduto += valor;
      } else {
        outrasDespesas += valor;
      }
    });

    const resultadoOperacional = receitas - custosProduto - outrasDespesas;
    const margem = receitas > 0 ? (resultadoOperacional / receitas) * 100 : 0;

    return {
      receitas,
      custosProduto,
      outrasDespesas,
      resultadoOperacional,
      margem
    };
  });
}

export function computeTopN(sales = [], expenses = []) {
  const key = `topn_${sales.length}_${expenses.length}`;
  return getCachedAnalytics(key, () => {
    const despesasMap = new Map();
    expenses.forEach(e => {
      const p = e.planoConta || "Sem plano";
      despesasMap.set(p, (despesasMap.get(p) || 0) + parseNum(e.valor));
    });

    const formasPgtoMap = new Map();
    sales.forEach(s => {
      const f = s.formaPagamento || "Outros";
      formasPgtoMap.set(f, (formasPgtoMap.get(f) || 0) + parseNum(s.totalVenda));
    });

    const sortMap = (map) => Array.from(map.entries()).sort((a,b) => b[1] - a[1]).slice(0, 10);

    return {
      topDespesas: sortMap(despesasMap),
      topFormasPgto: sortMap(formasPgtoMap)
    };
  });
}

export function computeAlerts(sales = [], expenses = [], accounts = [], stock = []) {
  const key = `alerts_${sales.length}_${expenses.length}_${accounts.length}_${stock.length}`;
  return getCachedAnalytics(key, () => {
    const alerts = [];
    
    const dre = computeDRE(sales, expenses);
    if (dre.margem < 0) {
      alerts.push({ tipo: "danger", mensagem: "Margem Operacional Negativa!" });
    } else if (dre.margem < 5) {
      alerts.push({ tipo: "warning", mensagem: "Margem Operacional Baixa (Abaixo de 5%)." });
    }

    let contasVencidas = 0;
    const hoje = new Date();
    accounts.forEach(a => {
      if (a.status !== "pago" && a.vencimento) {
        const d = new Date(a.vencimento);
        if (d < hoje) contasVencidas++;
      }
    });
    if (contasVencidas > 0) {
      alerts.push({ tipo: "danger", mensagem: `${contasVencidas} Conta(s) Vencida(s)!` });
    }

    let estoqueCritico = 0;
    stock.forEach(s => {
      if (parseNum(s.quantidade) < 100) estoqueCritico++;
    });
    if (estoqueCritico > 0) {
      alerts.push({ tipo: "warning", mensagem: `${estoqueCritico} Produto(s) com estoque baixo.` });
    }

    return alerts;
  });
}
