export const analyticsCache = new Map();

/**
 * Retorna o valor do cache se existir, caso contrario calcula e armazena.
 * @param {string} key Chave do cache baseada nos dados de entrada
 * @param {Function} computeFn Funcao de calculo
 */
export function getCachedAnalytics(key, computeFn) {
  if (analyticsCache.has(key)) {
    return analyticsCache.get(key);
  }
  const result = computeFn();
  analyticsCache.set(key, result);
  return result;
}

export function clearAnalyticsCache() {
  analyticsCache.clear();
}
