/**
 * RT-07 — Sub-navegação interna de hubs (sem novas APIs).
 */
export function mountHubShell(container, { tabs, activeTab, onTabChange, renderContent }) {
  if (!container) return;

  let currentTab = activeTab || tabs[0]?.id;

  container.innerHTML = `
    <div class="hub-shell hub-shell--premium">
      <nav class="hub-shell__tabs" role="tablist" aria-label="Seções"></nav>
      <div class="hub-shell__content" role="tabpanel"></div>
    </div>
  `;

  const tabsNav = container.querySelector(".hub-shell__tabs");
  const contentEl = container.querySelector(".hub-shell__content");

  function paintTabs() {
    tabsNav.innerHTML = tabs
      .map(
        (tab) => `
          <button
            type="button"
            class="hub-shell__tab${tab.id === currentTab ? " hub-shell__tab--active" : ""}"
            role="tab"
            aria-selected="${tab.id === currentTab}"
            data-hub-tab="${tab.id}"
          >${tab.label}</button>`
      )
      .join("");
  }

  function paintContent() {
    contentEl.innerHTML = "";
    renderContent(contentEl, currentTab);
  }

  tabsNav.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-hub-tab]");
    if (!btn || btn.dataset.hubTab === currentTab) return;
    currentTab = btn.dataset.hubTab;
    paintTabs();
    paintContent();
    onTabChange?.(currentTab);
  });

  paintTabs();
  paintContent();

  return {
    setTab(tabId) {
      if (!tabs.some((t) => t.id === tabId)) return;
      currentTab = tabId;
      paintTabs();
      paintContent();
    },
    getTab: () => currentTab,
    refresh: () => paintContent(),
  };
}
