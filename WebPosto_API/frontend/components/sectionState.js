/**
 * Estados visuais por seção — loading, erro com retry, sem alert() global.
 */

export function isTimeoutError(message) {
  const text = String(message || "").toLowerCase();
  return text.includes("timeout") || text.includes("aborted") || text.includes("abort");
}

export function friendlySectionError(message, sectionLabel = "esta seção") {
  if (isTimeoutError(message)) {
    return `A consulta de ${sectionLabel} demorou mais que o esperado. Os demais dados da página continuam disponíveis.`;
  }
  if (!message) return `Não foi possível carregar ${sectionLabel} no momento.`;
  if (String(message).startsWith("Timeout na requisicao")) {
    return `A consulta de ${sectionLabel} demorou mais que o esperado. Tente novamente.`;
  }
  return String(message);
}

export function renderSectionSkeleton({ title = "Carregando dados…", lines = 3 } = {}) {
  const bars = Array.from({ length: lines }, (_, i) => {
    const width = i === 0 ? "72%" : i === 1 ? "55%" : "40%";
    return `<span class="section-skeleton__bar" style="width:${width}"></span>`;
  }).join("");
  return `
    <div class="section-state section-state--loading" role="status" aria-live="polite">
      <div class="section-skeleton" aria-hidden="true">
        <span class="section-skeleton__bar section-skeleton__bar--hero"></span>
        ${bars}
      </div>
      <p class="section-state__hint">${title}</p>
    </div>`;
}

export function renderSectionError({
  title = "Não foi possível carregar",
  message = "Tente novamente em instantes.",
  retryId = "sectionRetryBtn",
  retryLabel = "Tentar novamente",
  icon = "⚠",
} = {}) {
  return `
    <div class="section-state section-state--error" role="alert">
      <div class="section-state__icon" aria-hidden="true">${icon}</div>
      <div class="section-state__body">
        <h3 class="section-state__title">${title}</h3>
        <p class="section-state__message">${message}</p>
        <button type="button" id="${retryId}" class="btn-primary section-state__retry">${retryLabel}</button>
      </div>
    </div>`;
}

export function bindSectionRetry(container, retryId, onRetry) {
  if (!container || typeof onRetry !== "function") return;
  container.querySelector(`#${retryId}`)?.addEventListener("click", () => onRetry());
}
