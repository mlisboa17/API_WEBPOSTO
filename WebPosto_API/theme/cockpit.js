/**
 * Logos Cockpit Lionda — KPIs Adelaide, filtros reais, CHAVE localStorage.
 */
(function (global) {
    'use strict';

    const STORAGE_KEY = 'WEBPOSTO_CHAVE';
    const STORAGE_GRUPOS = 'COCKPIT_GRUPOS_SELECIONADOS';
    const STORAGE_POSTOS = 'COCKPIT_POSTOS_SELECIONADOS';
    const REDE_NOME = 'LISBÔA';
    const KPI_IDS = ['kpiFat', 'kpiTax', 'kpiGal', 'kpiExp'];
    const POSTO_LABELS = {
        consolidado: 'LISBÔA — POSTO VIP RIO DOCE + POSTO CASA CAIADA',
        rio_doce: 'POSTO VIP RIO DOCE',
        casa_caiada: 'POSTO CASA CAIADA',
    };
    const POSTO_IDS_UI = ['consolidado', 'rio_doce', 'casa_caiada'];
    let gruposCatalogo = [];
    let gruposCatalogoRaw = [];
    let serverHasKey = false;
    let unidadeAtual = null;
    let dadosReaisAtivos = false;
    let ultimaRespostaMetrics = null;
    /** 'dia_atual' | 'periodo_custom' — controla buildMetricsQueryForDashboard */
    let consultaModoData = 'dia_atual';

    // Sempre inicia sem grupos persistidos para evitar filtro "fantasma".
    function resetFiltroGruposNoBoot() {
        try {
            global.localStorage.removeItem(STORAGE_GRUPOS);
        } catch (_) { /* ignore */ }
    }

    function isDadosReaisStrict(data) {
        if (!data) return false;
        return (
            data.status_api === 'dados_reais_live' &&
            data.fallback !== true &&
            data.dados_reais !== false
        );
    }

    function hasMetricPayload(data) {
        if (!data || data.status_api === 'demonstracao_offline') return false;
        const fat = parseFloat(data.faturamento_bruto);
        const gal = parseFloat(data.galonagem_total);
        return (
            data.dados_reais === true ||
            !isNaN(fat) ||
            !isNaN(gal) ||
            (data.qtd_abastecimentos || 0) > 0
        );
    }

    function shouldDisplayKpis(data) {
        return hasMetricPayload(data);
    }

    function setModoDadosReais(ativo, mensagem) {
        dadosReaisAtivos = !!ativo;
        const vendaCard = el('dashCardVenda');
        const gate = el('noDataGate');
        const cat = el('catalogoSection');
        const catGate = el('catalogoGateMsg');
        const por = el('porProdutoSection');
        const msg = el('noDataMessage');
        const partial = el('partialDataBanner');

        if (vendaCard) vendaCard.classList.toggle('hidden', !ativo);
        if (cat) cat.classList.toggle('hidden', !ativo);
        if (catGate) catGate.classList.toggle('hidden', ativo);
        if (gate) gate.classList.toggle('hidden', ativo);
        if (partial) partial.classList.add('hidden');
        if (!ativo && por) por.classList.add('hidden');
        if (msg && mensagem) msg.textContent = mensagem;
    }

    function setPartialWarning(data) {
        const partial = el('partialDataBanner');
        const text = el('partialDataText');
        if (!partial || !text) return;
        if (!data || isDadosReaisStrict(data)) {
            partial.classList.add('hidden');
            return;
        }
        if (!shouldDisplayKpis(data)) {
            partial.classList.add('hidden');
            return;
        }
        const msg =
            data.mensagem ||
            'Dados parciais — algumas unidades ou endpoints podem não ter respondido.';
        text.textContent = msg;
        partial.classList.remove('hidden');
    }

    function setDashboardLoading(loading) {
        const vendaCard = el('dashCardVenda');
        const refreshBtns = document.querySelectorAll('[data-action="refresh-dashboard"]');
        if (vendaCard) vendaCard.classList.toggle('dash-card--loading', loading);
        refreshBtns.forEach(function (btn) {
            btn.disabled = loading;
            btn.setAttribute('aria-busy', loading ? 'true' : 'false');
        });
        shimmer(loading);
    }

    function updateLastRefreshTime() {
        const node = el('lastUpdatedAt');
        if (!node) return;
        const now = new Date();
        node.textContent =
            'Atualizado às ' +
            pad2(now.getHours()) +
            ':' +
            pad2(now.getMinutes()) +
            ':' +
            pad2(now.getSeconds());
    }

    function renderKpiValues(data) {
        const fat = el('kpiFat');
        const tax = el('kpiTax');
        const gal = el('kpiGal');
        const exp = el('kpiExp');
        const fatPista = parseFloat(data.faturamento_bruto || 0) || 0;
        const fatLoja = parseFloat(data.faturamento_nao_combustivel || 0) || 0;
        const fatTotal = fatPista + fatLoja;

        if (fat) fat.textContent = fmtBRL(fatTotal);
        if (tax) tax.textContent = fmtBRL(data.credito_recuperavel);
        if (gal) gal.textContent = fmtL(data.galonagem_total);
        if (exp) exp.textContent = fmtBRL(data.despesas_caixa);

        const galMeta = el('kpiGalMeta');
        if (galMeta) {
            const ab = data.qtd_abastecimentos || 0;
            const vd = data.qtd_itens_venda || 0;
            galMeta.textContent =
                vd > 0
                    ? 'Pista ' + ab + ' abast. · PDV ' + vd + ' itens'
                    : ab + ' abastecimento(s)';
        }
        const expMeta = el('kpiExpMeta');
        if (expMeta) {
            expMeta.textContent = 'Movimentação de caixa';
        }
        const fatMeta = el('kpiFatMeta');
        if (fatMeta) {
            if (fatLoja > 0) {
                fatMeta.textContent =
                    'Pista ' + fmtBRL(fatPista) + ' + Loja ' + fmtBRL(fatLoja);
            } else {
                fatMeta.textContent = 'Somente pista/combustível';
            }
        }

        const vendaTitulo = el('vendaDiaTitulo');
        if (vendaTitulo) {
            const quando = isModoPeriodoCustom()
                ? getDescricaoPeriodoUI()
                : formatDateBR(getDiaConsulta(data));
            vendaTitulo.textContent =
                (isModoPeriodoCustom() ? 'Venda no período · ' : 'Venda do dia · ') + quando;
        }
        updateFiltroChips();
    }

    function normalizarNomePostoApi(nome) {
        const n = String(nome || '').toLowerCase();
        if (n.indexOf('rio') >= 0 && n.indexOf('doce') >= 0) return POSTO_LABELS.rio_doce;
        if (n.indexOf('caiada') >= 0) return POSTO_LABELS.casa_caiada;
        if (n.indexOf('lisbo') >= 0 || n.indexOf('grupo') >= 0) return REDE_NOME;
        return nome;
    }

    function getTituloUnidadeExibicao(unidade) {
        const selecao = getDescricaoPostosUI();
        if (!unidade) return selecao;
        const fant = String(unidade.fantasia || '').toUpperCase();
        const raz = String(unidade.razao_social || '').toUpperCase();
        if (
            unidade.chave_mascarada === 'MULTI_UNIDADE' ||
            fant.indexOf('GRUPO') >= 0 ||
            fant.indexOf('LISBO') >= 0 ||
            raz.indexOf('GRUPO') >= 0
        ) {
            return selecao;
        }
        return normalizarNomePostoApi(unidade.fantasia) || unidade.fantasia || selecao;
    }

    function renderUnidadePosto(unidade, metaGrupos) {
        unidadeAtual = unidade || null;
        const fant = el('postoFantasia');
        const raz = el('postoRazao');
        const cnpj = el('postoCnpj');
        const api = el('postoApiUrl');
        const ch = el('postoChaveHint');
        const gm = el('postoGruposMeta');

        if (!unidade) {
            if (fant) fant.textContent = 'Selecione uma filial';
            if (raz) raz.textContent = 'Aguardando consulta WebPosto';
            return;
        }

        if (fant) fant.textContent = getTituloUnidadeExibicao(unidade);
        if (raz) {
            raz.textContent =
                unidade.razao_social && unidade.razao_social !== unidade.fantasia
                    ? normalizarNomePostoApi(unidade.razao_social) || unidade.razao_social
                    : getDescricaoPostosUI();
        }
        if (cnpj) {
            cnpj.textContent = unidade.cnpj ? 'CNPJ ' + unidade.cnpj : 'CNPJ não informado';
        }
        if (api) api.textContent = 'API · ' + (unidade.base_url || 'WebPosto Quality');
        if (ch) ch.textContent = 'Chave · ' + (unidade.chave_mascarada || '—');
        if (gm && metaGrupos) {
            gm.textContent =
                metaGrupos.total +
                ' grupo(s) no cadastro' +
                (metaGrupos.comProdutos != null
                    ? ' · ' + metaGrupos.comProdutos + ' com produtos no índice'
                    : '');
        }
    }

    /** Forçar uso de CHAVE local desativado: sempre usar a chave do servidor (.env). */
    function appendApiKeyIfOverride(params) {
        // noop — não adiciona api_key localmente
    }

    function fmtBRL(n) {
        return (
            'R$ ' +
            Number(n || 0).toLocaleString('pt-BR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            })
        );
    }

    function fmtL(n) {
        return (
            Number(n || 0).toLocaleString('pt-BR', {
                maximumFractionDigits: 0,
            }) + ' L'
        );
    }

    function getToken() {
        // Override local desativado — sempre retorna vazio para forçar uso do .env no servidor
        return '';
    }

    function setToken(v) {
        const s = String(v || '').trim();
        if (s) global.localStorage.setItem(STORAGE_KEY, s);
        else global.localStorage.removeItem(STORAGE_KEY);
    }

    function el(id) {
        return document.getElementById(id);
    }

    function val(id) {
        const node = el(id);
        return node ? String(node.value || '').trim() : '';
    }

    function pad2(n) {
        return String(n).padStart(2, '0');
    }

    const FUSO_POSTO = 'America/Recife';

    function hojeISO() {
        return new Date().toLocaleDateString('en-CA', { timeZone: FUSO_POSTO });
    }

    function getDiaConsulta(data) {
        if (data && data.data_inicial) return String(data.data_inicial).slice(0, 10);
        if (data && data.data_final) return String(data.data_final).slice(0, 10);
        return hojeISO();
    }

    function labelDiaCorrente(data) {
        const iso = getDiaConsulta(data);
        const br = formatDateBR(iso);
        const hoje = hojeISO();
        if (iso === hoje) {
            return 'Dia corrente · ' + br;
        }
        return 'Dia · ' + br;
    }

    function addDaysISO(iso, days) {
        const d = new Date(iso + 'T12:00:00');
        d.setDate(d.getDate() + days);
        return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate());
    }

    function formatDateBR(iso) {
        if (!iso) return '—';
        const p = iso.split('-');
        if (p.length !== 3) return iso;
        return p[2] + '/' + p[1] + '/' + p[0];
    }

    function diasNoIntervalo(di, df) {
        if (!di || !df) return 0;
        const a = new Date(di + 'T12:00:00');
        const b = new Date(df + 'T12:00:00');
        return Math.max(1, Math.round((b - a) / 86400000) + 1);
    }

    function isModoPeriodoCustom() {
        return consultaModoData === 'periodo_custom';
    }

    function syncModoDataRadios() {
        const dia = el('modoDataDiaAtual');
        const per = el('modoDataPeriodo');
        if (dia) dia.checked = !isModoPeriodoCustom();
        if (per) per.checked = isModoPeriodoCustom();
    }

    function setModoDataConsulta(modo) {
        consultaModoData = modo === 'periodo_custom' ? 'periodo_custom' : 'dia_atual';
        syncModoDataRadios();
        updatePeriodoResumo();
        updateFiltroChips();
    }

    function getDescricaoPeriodoUI() {
        if (!isModoPeriodoCustom()) {
            return 'Hoje · ' + formatDateBR(hojeISO()) + ' (Recife)';
        }
        const di = val('dataInicialFilter');
        const df = val('dataFinalFilter');
        if (di && df) {
            return formatDateBR(di) + ' → ' + formatDateBR(df);
        }
        return 'Período personalizado';
    }

    function getDescricaoVendaUI() {
        const tipo = val('tipoProdutoFilter') || 'todos';
        const af = el('excluirAfericaoFilter');
        const partes = [];
        partes.push(tipo === 'combustivel' ? 'Só combustível' : 'Combustível + loja');
        if (af && af.checked) partes.push('sem aferição');
        else partes.push('com aferição');
        return partes.join(' · ');
    }

    function updatePeriodoResumo() {
        const label = el('periodoResumoLabel');
        const info = el('periodoDiasInfo');
        const hoje = hojeISO();
        const di = val('dataInicialFilter');
        const df = val('dataFinalFilter');
        if (label) {
            label.textContent = isModoPeriodoCustom()
                ? 'Período · ' + getDescricaoPeriodoUI()
                : 'Dia atual · ' + formatDateBR(hoje) + ' (Recife)';
        }
        if (info && di && df) {
            info.textContent = isModoPeriodoCustom()
                ? 'Visão geral usa ' +
                  formatDateBR(di) +
                  ' → ' +
                  formatDateBR(df) +
                  ' (' +
                  diasNoIntervalo(di, df) +
                  ' dia(s)).'
                : 'Visão geral usa o dia atual (' +
                  formatDateBR(hoje) +
                  '). Os campos abaixo ficam prontos para quando você ativar período personalizado.';
        }
        const vendaTitulo = el('vendaDiaTitulo');
        if (vendaTitulo && ultimaRespostaMetrics) {
            vendaTitulo.textContent =
                (isModoPeriodoCustom() ? 'Venda no período · ' : 'Venda do dia · ') +
                getDescricaoPeriodoUI().replace('Hoje · ', '');
        }
    }

    function setActiveDatePreset(preset) {
        document.querySelectorAll('.date-preset').forEach(function (btn) {
            btn.classList.toggle(
                'date-preset--active',
                btn.getAttribute('data-preset') === preset
            );
        });
    }

    function applyDatePreset(preset, skipRefresh) {
        const hoje = hojeISO();
        let di = hoje;
        let df = hoje;
        let periodo = 'hoje';

        if (preset === 'ontem') {
            di = df = addDaysISO(hoje, -1);
            periodo = 'hoje';
        } else if (preset === '7d') {
            di = addDaysISO(hoje, -6);
            df = hoje;
            periodo = '7d';
        } else if (preset === 'mensal') {
            di = addDaysISO(hoje, -29);
            df = hoje;
            periodo = 'mensal';
        } else if (preset === 'mes_atual') {
            const now = new Date();
            di = now.getFullYear() + '-' + pad2(now.getMonth() + 1) + '-01';
            df = hoje;
            periodo = 'mensal';
        }

        const diEl = el('dataInicialFilter');
        const dfEl = el('dataFinalFilter');
        const pEl = el('periodoFilter');
        if (diEl) diEl.value = di;
        if (dfEl) dfEl.value = df;
        if (pEl) pEl.value = periodo;
        setActiveDatePreset(preset);
        const infoEl = el('periodoDiasInfo');
        updatePeriodoResumo();
        if (!skipRefresh && isModoPeriodoCustom()) {
            updateDashboard();
        }
    }

    function initDateFilters() {
        applyDatePreset('hoje', true);
    }

    function isMobileNav() {
        return global.matchMedia('(max-width: 768px)').matches;
    }

    function setSidebarOpen(open) {
        const sidebar = el('appSidebar');
        const backdrop = el('sidebarBackdrop');
        const toggle = el('btnMenuToggle');
        if (sidebar) sidebar.classList.toggle('is-open', open);
        if (backdrop) backdrop.classList.toggle('is-visible', open);
        document.body.classList.toggle('sidebar-open-mobile', open && isMobileNav());
        if (toggle) toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    }

    function closeSidebar() {
        setSidebarOpen(false);
    }

    function toggleSidebar() {
        const sidebar = el('appSidebar');
        setSidebarOpen(!(sidebar && sidebar.classList.contains('is-open')));
    }

    function getActiveCockpitView() {
        const active = document.querySelector('.nav-item[data-view].nav-item--active');
        return active ? active.getAttribute('data-view') : 'overview';
    }

    function getDescricaoPostosUI() {
        const ids = getPostosSelecionados();
        if (ids.includes('consolidado')) {
            return POSTO_LABELS.consolidado;
        }
        return ids.map(function (id) {
            return POSTO_LABELS[id] || id;
        }).join(' + ');
    }

    function getDescricaoFilialUI() {
        const f = val('filialFilter');
        if (!f) {
            return 'Todas as filiais do(s) posto(s) selecionado(s)';
        }
        return 'Somente filial(is) código: ' + f;
    }

    function getNomesGruposSelecionados() {
        const sel = getGruposSelecionados();
        return sel.map(function (cod) {
            const g = gruposCatalogoRaw.find(function (x) {
                return String(x.codigo) === String(cod);
            });
            return g ? g.nome || 'Grupo ' + cod : 'Grupo ' + cod;
        });
    }

    function temFiltroGruposAtivo() {
        return getGruposSelecionados().length > 0;
    }

    function getDescricaoGruposUI() {
        if (!temFiltroGruposAtivo()) {
            return 'Todos os grupos — venda completa do dia (sem filtro)';
        }
        const nomes = getNomesGruposSelecionados();
        return (
            'Filtro ativo: ' +
            nomes.join(', ') +
            ' — os KPIs mostram só produtos deste(s) grupo(s)'
        );
    }

    function updateFiltroChips() {
        const chipPosto = el('chipPosto');
        const chipFilial = el('chipFilial');
        const chipGrupo = el('chipGrupo');
        const posto = getDescricaoPostosUI();
        const filial = getDescricaoFilialUI();
        const grupo = temFiltroGruposAtivo()
            ? getNomesGruposSelecionados().join(', ')
            : 'todos os grupos';
        if (chipPosto) chipPosto.textContent = posto;
        if (chipFilial) chipFilial.textContent = filial;
        if (chipGrupo) chipGrupo.textContent = grupo;
        const filtros = el('dashCardFiltros');
        if (filtros) {
            filtros.textContent =
                posto +
                ' · Filial ' +
                filial +
                ' · ' +
                grupo +
                ' · ' +
                getDescricaoPeriodoUI() +
                ' · ' +
                getDescricaoVendaUI();
        }
    }

    function limparFiltroGrupos() {
        try {
            global.localStorage.removeItem(STORAGE_GRUPOS);
        } catch (_) { /* ignore */ }
        const list = el('gruposFilterList');
        if (list) {
            list.querySelectorAll('.grupo-card input[type=checkbox]').forEach(function (cb) {
                cb.checked = false;
                const card = cb.closest('.grupo-card');
                if (card) card.classList.remove('grupo-card--on');
            });
        }
        atualizarResumoGrupos();
        updateContextoConsulta();
        updateGruposFiltroBanner();
        updateDashboard();
    }

    function updateGruposFiltroBanner() {
        const banner = el('gruposFiltroBanner');
        const text = el('gruposFiltroText');
        const btnStrip = el('btnLimparGruposStrip');
        const ativo = temFiltroGruposAtivo();
        if (btnStrip) btnStrip.classList.toggle('hidden', !ativo);
        if (!banner || !text) return;
        if (!ativo) {
            banner.classList.add('hidden');
            return;
        }
        const nomes = getNomesGruposSelecionados();
        text.textContent =
            'Os KPIs estão filtrados pelo grupo “' +
            nomes.join('”, “') +
            '”. Para ver a venda completa do dia (combustível + loja + todos os grupos), remova o filtro.';
        banner.classList.remove('hidden');
    }

    function updateContextoConsulta(metricsData) {
        if (metricsData) {
            ultimaRespostaMetrics = metricsData;
        }
        updateGruposFiltroBanner();
        updateFiltroChips();
        renderFilialPills();
    }

    function isFilialPillAtiva(id) {
        const sel = getPostosSelecionados();
        if (id === 'consolidado') return sel.includes('consolidado');
        return !sel.includes('consolidado') && sel.includes(id);
    }

    function selecionarFilialPill(id) {
        const all = el('postoGrupoLisboaAll');
        const list = el('postoFilterList');
        if (!list) return;
        if (id === 'consolidado') {
            if (all) all.checked = true;
            list.querySelectorAll('input.posto-unit-cb').forEach(function (cb) {
                cb.checked = false;
            });
        } else {
            if (all) all.checked = false;
            list.querySelectorAll('input.posto-unit-cb').forEach(function (cb) {
                cb.checked = cb.getAttribute('data-posto-id') === id;
            });
        }
        salvarPostosSelecionados();
        atualizarResumoPostos();
        updateDashboard();
    }

    function renderFilialPills() {
        const bar = el('filialPillsBar');
        if (!bar) return;
        const opcoes = [
            { id: 'consolidado', label: 'LISBÔA (todas)' },
            { id: 'rio_doce', label: POSTO_LABELS.rio_doce },
            { id: 'casa_caiada', label: POSTO_LABELS.casa_caiada },
        ];
        bar.innerHTML = '<span class="filial-pills__label">Filial · clique para consultar</span>';
        opcoes.forEach(function (op) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'filial-pill' + (isFilialPillAtiva(op.id) ? ' filial-pill--on' : '');
            btn.textContent = op.label;
            btn.setAttribute('data-filial-id', op.id);
            btn.addEventListener('click', function () {
                selecionarFilialPill(op.id);
            });
            bar.appendChild(btn);
        });
    }

    const FILTER_VIEWS = ['unidades', 'periodo', 'grupos', 'venda'];

    function isFilterView(view) {
        return FILTER_VIEWS.indexOf(view) >= 0;
    }

    function setNavSubmenuFiltrosOpen(open) {
        const submenu = el('navSubmenuFiltros');
        const list = el('navSubmenuFiltrosList');
        const toggle = el('btnNavFiltrosToggle');
        if (!submenu || !list || !toggle) return;
        submenu.classList.toggle('nav-submenu--open', open);
        list.hidden = !open;
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    }

    function syncNavSubmenuFiltros(view) {
        const toggle = el('btnNavFiltrosToggle');
        if (toggle) {
            toggle.classList.toggle('nav-submenu__toggle--active', isFilterView(view));
        }
        if (isFilterView(view)) {
            setNavSubmenuFiltrosOpen(true);
        }
    }

    function showCockpitView(view) {
        document.querySelectorAll('.cockpit-view').forEach(function (panel) {
            panel.classList.add('hidden');
        });
        const target = el('view-' + view);
        if (target) target.classList.remove('hidden');
        document.querySelectorAll('.nav-item[data-view]').forEach(function (btn) {
            btn.classList.toggle('nav-item--active', btn.getAttribute('data-view') === view);
        });
        syncNavSubmenuFiltros(view);
        updateContextoConsulta();
        if (view === 'catalogo' && dadosReaisAtivos) {
            carregarProdutosDoPosto();
        }
        if (view === 'grupos' && !gruposCatalogoRaw.length) {
            carregarGruposProduto();
        }
        if (isMobileNav()) closeSidebar();
    }

    function bindMobileNav() {
        const toggle = el('btnMenuToggle');
        const closeBtn = el('btnSidebarClose');
        const backdrop = el('sidebarBackdrop');
        if (toggle) toggle.addEventListener('click', toggleSidebar);
        if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
        if (backdrop) backdrop.addEventListener('click', closeSidebar);
        document.addEventListener('keydown', function (ev) {
            if (ev.key === 'Escape') closeSidebar();
        });
        global.matchMedia('(max-width: 768px)').addEventListener('change', function () {
            if (!isMobileNav()) closeSidebar();
        });
    }

    function bindRefreshButtons() {
        document.querySelectorAll('[data-action="refresh-dashboard"]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                updateDashboard();
                if (isMobileNav()) closeSidebar();
            });
        });
    }

    function bindSidebarNav() {
        document.querySelectorAll('.nav-item[data-view]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                showCockpitView(btn.getAttribute('data-view'));
            });
        });
        const filtrosToggle = el('btnNavFiltrosToggle');
        if (filtrosToggle) {
            filtrosToggle.addEventListener('click', function () {
                const list = el('navSubmenuFiltrosList');
                const open = list && list.hidden;
                setNavSubmenuFiltrosOpen(!!open);
            });
        }
        bindRefreshButtons();
        bindMobileNav();
    }

    function bindQuickActions() {
        const irFiltros = el('btnIrFiltros');
        if (irFiltros) {
            irFiltros.addEventListener('click', function () {
                showCockpitView('unidades');
            });
        }
        document.querySelectorAll('[data-action="goto-overview"]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                updateDashboard();
                showCockpitView('overview');
            });
        });
    }

    function bindModoDataConsulta() {
        syncModoDataRadios();
        document.querySelectorAll('input[name="modoDataConsulta"]').forEach(function (radio) {
            radio.addEventListener('change', function () {
                setModoDataConsulta(radio.value);
                if (isModoPeriodoCustom()) {
                    updateDashboard();
                } else {
                    applyDatePreset('hoje', true);
                    updateDashboard();
                }
            });
        });
        const aplicar = el('btnAplicarPeriodo');
        if (aplicar) {
            aplicar.addEventListener('click', function () {
                setModoDataConsulta('periodo_custom');
                updateDashboard();
                showCockpitView('overview');
            });
        }
        const voltar = el('btnVoltarDiaAtual');
        if (voltar) {
            voltar.addEventListener('click', function () {
                setModoDataConsulta('dia_atual');
                applyDatePreset('hoje', true);
                updateDashboard();
                showCockpitView('overview');
            });
        }
    }

    function buildMetricsQueryForDashboard() {
        if (isModoPeriodoCustom()) {
            return buildMetricsQuery();
        }
        return buildMetricsQueryHoje();
    }

    function bindDatePresets() {
        document.querySelectorAll('.date-preset').forEach(function (btn) {
            btn.addEventListener('click', function () {
                applyDatePreset(btn.getAttribute('data-preset'));
            });
        });
    }

    function appendFiltrosComuns(params) {
        const tipo = val('tipoProdutoFilter');
        if (tipo && tipo !== 'todos') params.set('tipo_produto', tipo);
        const filial = val('filialFilter');
        if (filial) params.set('filial', filial);
        const af = el('excluirAfericaoFilter');
        if (af && !af.checked) params.set('excluir_afericao', 'false');
        const grupos = getGruposSelecionados();
        if (grupos.length) params.set('grupos', grupos.join(','));
        const postos = getPostosSelecionados();
        if (postos.length) params.set('posto', postos.join(','));
        appendApiKeyIfOverride(params);
        return params;
    }

    /** Visão geral: sempre venda do dia atual. */
    function buildMetricsQueryHoje() {
        const hoje = hojeISO();
        const params = new URLSearchParams();
        params.set('periodo', 'hoje');
        params.set('data_inicial', hoje);
        params.set('data_final', hoje);
        return appendFiltrosComuns(params);
    }

    function buildMetricsQuery() {
        const p = val('periodoFilter') || 'mensal';
        const params = new URLSearchParams();
        params.set('periodo', p);
        const di = val('dataInicialFilter');
        const df = val('dataFinalFilter');
        if (di) params.set('data_inicial', di);
        if (df) params.set('data_final', df);
        return appendFiltrosComuns(params);
    }

    function getPostosSelecionados() {
        const all = el('postoGrupoLisboaAll');
        if (all && all.checked) return ['consolidado'];
        const list = el('postoFilterList');
        if (!list) return ['consolidado'];
        const ids = [];
        list.querySelectorAll('input.posto-unit-cb:checked').forEach(function (cb) {
            const id = cb.getAttribute('data-posto-id');
            if (id && POSTO_IDS_UI.indexOf(id) >= 0 && id !== 'consolidado') ids.push(id);
        });
        return ids.length ? ids : ['consolidado'];
    }

    function salvarPostosSelecionados() {
        try {
            global.localStorage.setItem(STORAGE_POSTOS, JSON.stringify(getPostosSelecionados()));
        } catch (e) {
            /* ignore */
        }
    }

    function restaurarPostosSelecionados() {
        let saved = [];
        try {
            saved = JSON.parse(global.localStorage.getItem(STORAGE_POSTOS) || '[]');
        } catch (e) {
            saved = [];
        }
        if (!Array.isArray(saved) || !saved.length) return;
        saved = saved.filter(function (id) {
            return POSTO_IDS_UI.indexOf(id) >= 0;
        });
        if (!saved.length) return;

        const all = el('postoGrupoLisboaAll');
        const list = el('postoFilterList');
        if (!list) return;

        if (saved.includes('consolidado')) {
            if (all) all.checked = true;
            list.querySelectorAll('input.posto-unit-cb').forEach(function (cb) {
                cb.checked = false;
            });
        } else {
            if (all) all.checked = false;
            list.querySelectorAll('input.posto-unit-cb').forEach(function (cb) {
                const id = cb.getAttribute('data-posto-id');
                cb.checked = saved.includes(id);
            });
        }
        atualizarResumoPostos();
        updateContextoConsulta();
    }

    function atualizarResumoPostos() {
        const summary = el('postoFilterSummary');
        const masterCard = el('unitCardGrupoLisboa');
        if (!summary) return;
        if (masterCard) {
            const all = el('postoGrupoLisboaAll');
            masterCard.classList.toggle('unit-card--master', !!(all && all.checked));
        }
        const postos = getPostosSelecionados();
        if (postos.includes('consolidado')) {
            summary.textContent =
                REDE_NOME + ' · POSTO VIP RIO DOCE + POSTO CASA CAIADA';
        } else {
            const nomes = postos.map(function (id) {
                return POSTO_LABELS[id] || id;
            });
            summary.textContent =
                nomes.length > 1
                    ? REDE_NOME + ' · ' + nomes.join(' + ')
                    : nomes[0] || REDE_NOME;
        }
        updateContextoConsulta();
    }

    function bindPostosPanel() {
        const all = el('postoGrupoLisboaAll');
        const list = el('postoFilterList');
        if (!list) return;

        if (all) {
            all.addEventListener('change', function () {
                if (all.checked) {
                    list.querySelectorAll('input.posto-unit-cb').forEach(function (cb) {
                        cb.checked = false;
                    });
                }
                salvarPostosSelecionados();
                atualizarResumoPostos();
                updateDashboard();
            });
        }

        list.querySelectorAll('input.posto-unit-cb').forEach(function (cb) {
            cb.addEventListener('change', function () {
                if (cb.checked && all) all.checked = false;
                salvarPostosSelecionados();
                atualizarResumoPostos();
                updateDashboard();
            });
        });

        restaurarPostosSelecionados();
    }

    function buildProdutosQuery() {
        const params = new URLSearchParams({
            pagina: '1',
            limite: '200',
            todos: 'true',
        });
        const desc = val('descricaoProdutoFilter');
        const grupos = getGruposSelecionados();
        if (grupos.length) params.set('grupos', grupos.join(','));
        if (desc) params.set('descricao', desc);
        appendApiKeyIfOverride(params);
        return params;
    }

    function dedupeProdutosCatalogo(produtos) {
        const map = new Map();
        (produtos || []).forEach(function (prod) {
            const id = String(prod.id != null ? prod.id : prod.codigo || '');
            if (!id) return;
            if (!map.has(id)) {
                map.set(id, prod);
            }
        });
        return Array.from(map.values()).sort(function (a, b) {
            return String(a.descricao || '').localeCompare(String(b.descricao || ''), 'pt-BR');
        });
    }

    function dedupePorProdutoRows(rows) {
        const map = {};
        (rows || []).forEach(function (row) {
            const cod = String(row.codigo != null ? row.codigo : row.nome || '');
            if (!cod) return;
            const litros = parseFloat(row.litros || 0) || 0;
            const fat = parseFloat(row.faturamento || 0) || 0;
            if (!map[cod]) {
                map[cod] = {
                    codigo: row.codigo,
                    nome: row.nome || 'Produto ' + cod,
                    litros: litros,
                    faturamento: fat,
                };
            } else {
                map[cod].litros += litros;
                map[cod].faturamento += fat;
            }
        });
        return Object.keys(map)
            .map(function (k) {
                return map[k];
            })
            .sort(function (a, b) {
                return (b.faturamento || 0) - (a.faturamento || 0);
            });
    }

    function getGruposSelecionados() {
        const list = el('gruposFilterList');
        if (!list) {
            try {
                const saved = JSON.parse(global.localStorage.getItem(STORAGE_GRUPOS) || '[]');
                return Array.isArray(saved) ? saved.map(String) : [];
            } catch (_) {
                return [];
            }
        }
        const out = [];
        list.querySelectorAll('input[type=checkbox][data-grupo-codigo]:checked').forEach(function (cb) {
            out.push(String(cb.getAttribute('data-grupo-codigo')));
        });
        return out;
    }

    function salvarGruposSelecionados() {
        try {
            global.localStorage.setItem(STORAGE_GRUPOS, JSON.stringify(getGruposSelecionados()));
        } catch (_) { /* ignore */ }
    }

    function isGrupoAtivo(g) {
        return (g.qtd_produtos || 0) > 0;
    }

    function ordenarGrupos(grupos) {
        return (grupos || []).slice().sort(function (a, b) {
            const aa = isGrupoAtivo(a) ? 1 : 0;
            const bb = isGrupoAtivo(b) ? 1 : 0;
            if (bb !== aa) return bb - aa;
            return (a.nome || '').localeCompare(b.nome || '', 'pt-BR');
        });
    }

    function contarGruposPorStatus(grupos) {
        let ativos = 0;
        let inativos = 0;
        (grupos || []).forEach(function (g) {
            if (isGrupoAtivo(g)) ativos += 1;
            else inativos += 1;
        });
        return { ativos: ativos, inativos: inativos, total: (grupos || []).length };
    }

    function getGruposStatusFilter() {
        const node = el('gruposStatusFilter');
        return node ? String(node.value || 'todos') : 'todos';
    }

    function atualizarResumoGrupos() {
        const summary = el('gruposFilterSummary');
        if (!summary) return;
        const sel = getGruposSelecionados();
        const stats = contarGruposPorStatus(gruposCatalogoRaw);
        if (!stats.total) {
            summary.textContent = 'Nenhum grupo no cadastro — clique em Recarregar';
            return;
        }
        if (!sel.length) {
            summary.textContent =
                stats.total +
                ' grupo(s) · ' +
                stats.ativos +
                ' ativo(s) · ' +
                stats.inativos +
                ' inativo(s) · selecione para filtrar Adelaide';
            return;
        }
        const nomes = gruposCatalogoRaw
            .filter(function (g) {
                return sel.indexOf(String(g.codigo)) >= 0;
            })
            .map(function (g) {
                return g.nome;
            });
        summary.textContent =
            sel.length +
            ' selecionado(s): ' +
            (nomes.slice(0, 4).join(', ') || sel.join(', ')) +
            (nomes.length > 4 ? '…' : '');
    }

    function filtrarGruposPorBusca(grupos) {
        const q = (val('gruposSearchInput') || '').toLowerCase();
        if (!q) return grupos;
        return grupos.filter(function (g) {
            const nome = (g.nome || '').toLowerCase();
            const cod = String(g.codigo);
            return nome.indexOf(q) >= 0 || cod.indexOf(q) >= 0;
        });
    }

    function filtrarGruposPorStatus(grupos) {
        const modo = getGruposStatusFilter();
        if (modo === 'ativos') {
            return grupos.filter(isGrupoAtivo);
        }
        if (modo === 'inativos') {
            return grupos.filter(function (g) {
                return !isGrupoAtivo(g);
            });
        }
        return grupos;
    }

    function renderListaGrupos(grupos) {
        const list = el('gruposFilterList');
        if (!list) return;
        gruposCatalogoRaw = ordenarGrupos(grupos || []);
        gruposCatalogo = gruposCatalogoRaw;

        const visiveis = filtrarGruposPorBusca(
            filtrarGruposPorStatus(gruposCatalogo)
        );

        if (!gruposCatalogo.length) {
            list.innerHTML =
                '<p class="text-amber-400 text-sm col-span-full p-3">Nenhum grupo no cadastro WebPosto — verifique a chave no .env e clique em Recarregar.</p>';
            atualizarResumoGrupos();
            return;
        }
        if (!visiveis.length) {
            list.innerHTML =
                '<p class="text-gray-500 text-sm col-span-full p-3">Nenhum grupo corresponde aos filtros atuais.</p>';
            atualizarResumoGrupos();
            return;
        }

        let saved = [];
        try {
            saved = JSON.parse(global.localStorage.getItem(STORAGE_GRUPOS) || '[]');
        } catch (_) {
            saved = [];
        }
        const savedSet = new Set((saved || []).map(String));
        list.innerHTML = '';

        visiveis.forEach(function (g) {
            const cod = String(g.codigo);
            const qtd = g.qtd_produtos || 0;
            const ativo = isGrupoAtivo(g);
            const checked = savedSet.size ? savedSet.has(cod) : false;
            const card = document.createElement('label');
            card.className =
                'grupo-card' +
                (checked ? ' grupo-card--on' : '') +
                (ativo ? '' : ' grupo-card--inativo');
            card.setAttribute('data-grupo-nome', (g.nome || '').toLowerCase());
            card.setAttribute('data-grupo-ativo', ativo ? '1' : '0');
            card.innerHTML =
                '<input type="checkbox" data-grupo-codigo="' +
                cod +
                '"' +
                (checked ? ' checked' : '') +
                '>' +
                '<div><div class="grupo-card__nome">' +
                (g.nome || 'Grupo ' + cod) +
                '</div><div class="grupo-card__meta">Cód. ' +
                cod +
                '</div><div class="grupo-card__badges">' +
                '<span class="grupo-badge grupo-badge--status ' +
                (ativo ? 'grupo-badge--ativo' : 'grupo-badge--inativo') +
                '">' +
                (ativo ? 'Ativo' : 'Inativo') +
                '</span><span class="grupo-badge">' +
                qtd +
                ' produto(s)</span></div></div>';

            const cb = card.querySelector('input');
            cb.addEventListener('change', function () {
                card.classList.toggle('grupo-card--on', cb.checked);
                salvarGruposSelecionados();
                atualizarResumoGrupos();
                updateContextoConsulta();
                updateDashboard();
            });
            list.appendChild(card);
        });
        atualizarResumoGrupos();
        updateContextoConsulta();
    }

    async function carregarGruposProduto() {
        const summary = el('gruposFilterSummary');
        if (summary) summary.textContent = 'Carregando todos os grupos (GET /INTEGRACAO/GRUPO)…';
        const params = new URLSearchParams();
        appendApiKeyIfOverride(params);
        try {
            const res = await fetch('/api/v1/webposto/grupos-produto?' + params.toString());
            const data = await res.json();
            if (!res.ok) {
                const msg = data.detail || 'Falha ao carregar grupos';
                if (summary) summary.textContent = msg;
                return;
            }
            renderUnidadePosto(data.unidade, {
                total: data.total_grupos_sistema || data.total_grupos || 0,
                comProdutos: data.grupos_com_produtos_catalogo,
            });
            const total = data.total_grupos_sistema || data.total_grupos || 0;
            if (summary) {
                summary.textContent =
                    total +
                    ' grupo(s) cadastrados · ' +
                    (data.grupos_com_produtos_catalogo || 0) +
                    ' com produtos indexados · ' +
                    (data.total_produtos_indexados || 0) +
                    ' produto(s) varridos';
            }
            renderListaGrupos(data.grupos || []);
        } catch (e) {
            if (summary) summary.textContent = 'Erro: ' + e.message;
        }
    }

    function setConnStatus(ok, detail) {
        const top = el('connStatusTop');
        const text = detail || (ok ? 'Conexão ativa · WebPosto' : 'Sem conexão');
        if (top) {
            top.textContent = text;
            top.className = ok ? 'text-xs text-emerald-400' : 'text-xs text-amber-400';
        }
    }

    function shimmer(on) {
        KPI_IDS.forEach(function (id) {
            const node = el(id);
            if (!node) return;
            if (on) {
                node.classList.add('shimmer', 'text-transparent');
            } else {
                node.classList.remove('shimmer', 'text-transparent');
            }
        });
    }

    function renderPorProduto(rows, periodoLabel, metricsData) {
        const section = el('porProdutoSection');
        const tbody = el('porProdutoBody');
        const meta = el('porProdutoPeriodo');
        if (!section || !tbody) return;
        const unicos = dedupePorProdutoRows(rows);
        if (!unicos.length) {
            section.classList.add('hidden');
            return;
        }
        section.classList.remove('hidden');
        if (meta) {
            meta.textContent =
                unicos.length +
                ' produto(s) no dia' +
                (rows && rows.length > unicos.length
                    ? ' · ' + (rows.length - unicos.length) + ' duplicata(s) removida(s)'
                    : '');
        }
        tbody.innerHTML = '';
        unicos.forEach(function (row) {
            const tr = document.createElement('tr');
            tr.innerHTML =
                '<td class="omie-cell-code">' +
                row.codigo +
                '</td><td>' +
                row.nome +
                '</td><td class="text-right">' +
                fmtL(row.litros) +
                '</td><td class="text-right omie-cell-money">' +
                fmtBRL(row.faturamento) +
                '</td>';
            tbody.appendChild(tr);
        });
    }

    async function carregarOpcoesProduto() {
        const sel = el('tipoProdutoFilter');
        if (!sel) return;
        try {
            const res = await fetch('/api/v1/dashboard/filtros');
            const meta = await res.json();
            const base = sel.querySelectorAll('option').length;
            if (base > 2) return;
            (meta.combustiveis_catalogo || []).forEach(function (c) {
                const opt = document.createElement('option');
                opt.value = 'codigo:' + c.codigo;
                opt.textContent = c.nome;
                sel.appendChild(opt);
            });
        } catch (e) {
            console.warn('Filtros meta indisponível', e);
        }
    }

    async function loadServerConfig() {
        try {
            const r = await fetch('/api/config');
            if (!r.ok) return;
            const cfg = await r.json();
            serverHasKey = !!cfg.has_key;
            global.__WP_SERVER_HAS_KEY__ = serverHasKey;
        } catch (_) { /* ignore */ }
    }

    async function checkHealth() {
        await loadServerConfig();
        try {
            const r = await fetch('/health');
            const h = await r.json();
            if (h.status === 'healthy' && serverHasKey) {
                setConnStatus(true, 'WebPosto · chave do .env ativa');
            } else if (h.status === 'healthy') {
                setConnStatus(false, 'Configure WEBPOSTO_API_KEY no .env');
            } else {
                setConnStatus(false, 'Configure WEBPOSTO_API_KEY no .env');
            }
            const wr = await fetch('/api/health/webposto');
            const w = await wr.json();
            if (w.ok) {
                setConnStatus(true, 'WebPosto validado · HTTP ' + w.status_code + ' (.env)');
            } else if (global.__WP_FORCE_LOCAL_CHAVE__ && getToken()) {
                setConnStatus(false, 'Override local rejeitado — use .env');
            }
        } catch (e) {
            setConnStatus(false, 'Servidor offline — python src/presentation/app.py');
        }
    }

    let dashboardRequestId = 0;

    async function updateDashboard() {
        const reqId = ++dashboardRequestId;
        const url = '/api/v1/adelaide/metrics?' + buildMetricsQueryForDashboard().toString();
        const hadKpis = dadosReaisAtivos;
        setDashboardLoading(true);
        if (!hadKpis) {
            setModoDadosReais(false, 'Sincronizando com a API WebPosto…');
        }
        const badge = el('statusBadge');
        if (badge) {
            badge.textContent = 'Sincronizando…';
            badge.className = 'status-badge status-badge--sync';
        }

        try {
            const res = await fetch(url, { cache: 'no-store' });
            const data = await res.json();
            if (reqId !== dashboardRequestId) return;

            setDashboardLoading(false);

            if (data.unidade) {
                renderUnidadePosto(data.unidade, null);
            }
            updatePeriodoResumo();

            if (!res.ok) {
                const msg =
                    typeof data.detail === 'string'
                        ? data.detail
                        : JSON.stringify(data.detail || data);
                if (badge) {
                    badge.textContent = 'Erro ' + res.status;
                    badge.className = 'status-badge status-badge--error';
                }
                setConnStatus(false, msg);
                setModoDadosReais(false, msg);
                const alert = el('alertBox');
                if (alert) {
                    alert.textContent = msg;
                    alert.classList.remove('hidden');
                }
                return;
            }

            if (!shouldDisplayKpis(data)) {
                const msg =
                    data.mensagem ||
                    'Sem métricas no período — verifique chave no .env e filtros.';
                setModoDadosReais(false, msg);
                if (badge) {
                    badge.textContent = 'Sem dados';
                    badge.className = 'status-badge status-badge--warn';
                }
                setConnStatus(false, msg);
                const alert = el('alertBox');
                if (alert) {
                    alert.textContent = msg;
                    alert.classList.remove('hidden');
                }
                return;
            }

            setModoDadosReais(true);
            dadosReaisAtivos = true;
            renderKpiValues(data);
            setPartialWarning(data);

            const posto = data.unidade && data.unidade.fantasia ? data.unidade.fantasia : '';
            const live = isDadosReaisStrict(data);
            if (badge) {
                badge.textContent =
                    (live ? 'LIVE' : 'PARCIAL') +
                    ' · ' +
                    (data.periodo || '') +
                    (posto ? ' · ' + posto : '');
                badge.className = live
                    ? 'status-badge status-badge--live'
                    : 'status-badge status-badge--warn';
            }

            setConnStatus(
                true,
                (live ? 'Dados reais' : 'Dados parciais') + ' · ' + (posto || 'WebPosto')
            );
            renderPorProduto(data.por_produto, data.periodo, data);
            updateLastRefreshTime();
            updateContextoConsulta(data);
            if (getActiveCockpitView() === 'catalogo') {
                await carregarProdutosDoPosto();
            }

            const alert = el('alertBox');
            if (alert) alert.classList.add('hidden');
        } catch (err) {
            if (reqId !== dashboardRequestId) return;
            setDashboardLoading(false);
            setModoDadosReais(false, err.message);
            setConnStatus(false, err.message);
            const badge = el('statusBadge');
            if (badge) {
                badge.textContent = 'Falha';
                badge.className = 'status-badge status-badge--error';
            }
            console.error(err);
        }
    }

    async function carregarProdutosDoPosto() {
        const tbody = el('fiscalTable');
        if (!tbody || !dadosReaisAtivos) return;

        const catBadge = el('catalogoStatusBadge');
        if (catBadge) catBadge.textContent = 'Carregando catálogo completo (sem repetir códigos)…';

        const url = '/api/v1/webposto/produtos?' + buildProdutosQuery().toString();

        try {
            const response = await fetch(url);
            const data = await response.json();
            if (!response.ok) {
                tbody.innerHTML =
                    '<tr><td colspan="5" class="p-6 text-center text-amber-400">' +
                    (data.detail || 'Catálogo indisponível') +
                    '</td></tr>';
                return;
            }
            const produtos = dedupeProdutosCatalogo(data.produtos || []);
            if (!produtos.length) {
                tbody.innerHTML =
                    '<tr><td colspan="5" class="p-6 text-center text-gray-600">Nenhum produto no filtro</td></tr>';
                return;
            }

            tbody.innerHTML = '';
            produtos.forEach(function (prod) {
                const isMonofasico =
                    prod.cst_icms === '060' ||
                    prod.cst_icms === '60' ||
                    prod.cst_icms === '061';
                const statusTexto = isMonofasico ? '✓ Homologado' : '⚠ Alerta';
                const statusClass = isMonofasico
                    ? 'text-emerald-400 bg-emerald-950/40'
                    : 'text-red-400 bg-red-950/40';

                const tr = document.createElement('tr');
                tr.className = 'hover:bg-white/[0.02] transition-colors';
                tr.innerHTML =
                    '<td class="p-4 text-cyan-400 font-bold">' +
                    prod.id +
                    '</td><td class="p-4 font-sans font-bold text-white">' +
                    prod.descricao +
                    '<span class="block text-[10px] text-gray-500 font-mono font-normal">EAN: ' +
                    (prod.codigo_barra || '—') +
                    ' | Grupo: ' +
                    (prod.nome_grupo || 'GERAL') +
                    '</span></td><td class="p-4 text-gray-300">R$ ' +
                    parseFloat(prod.preco_venda || 0).toLocaleString('pt-BR', {
                        minimumFractionDigits: 2,
                    }) +
                    '</td><td class="p-4 text-gray-400 font-mono">' +
                    (prod.ncm || '—') +
                    '</td><td class="p-4 text-right font-sans"><span class="text-xs font-bold px-2 py-1 rounded-md ' +
                    statusClass +
                    '">' +
                    statusTexto +
                    '</span></td>';
                tbody.appendChild(tr);
            });

            if (catBadge && data.fonte === 'webposto_integracao') {
                catBadge.textContent =
                    'Catálogo: ' +
                    produtos.length +
                    ' produto(s) único(s)' +
                    (data.produtos && data.produtos.length > produtos.length
                        ? ' · ' + (data.produtos.length - produtos.length) + ' repetido(s) ignorado(s)'
                        : '') +
                    ' · filial conforme menu Filiais';
            }
        } catch (err) {
            console.error('Catálogo:', err);
            tbody.innerHTML =
                '<tr><td colspan="5" class="p-6 text-center text-red-400">Falha ao carregar catálogo</td></tr>';
        }
    }

    function applyToken() {
        // Campo de override removido — manter compatibilidade sem efeito.
        global.__WP_FORCE_LOCAL_CHAVE__ = false;
        checkHealth();
        carregarGruposProduto();
        updateDashboard();
    }

    function bindGruposPanel() {
        const ativosBtn = el('gruposSelectAtivosBtn');
        const clearBtn = el('gruposClearBtn');
        const reloadBtn = el('gruposReloadBtn');
        const search = el('gruposSearchInput');
        const statusFilter = el('gruposStatusFilter');
        if (ativosBtn) {
            ativosBtn.addEventListener('click', function () {
                const list = el('gruposFilterList');
                if (!list) return;
                list.querySelectorAll('.grupo-card').forEach(function (card) {
                    if (card.getAttribute('data-grupo-ativo') !== '1') return;
                    const cb = card.querySelector('input[type=checkbox]');
                    if (!cb) return;
                    cb.checked = true;
                    card.classList.add('grupo-card--on');
                });
                salvarGruposSelecionados();
                atualizarResumoGrupos();
                updateContextoConsulta();
                updateDashboard();
            });
        }
        if (statusFilter) {
            statusFilter.addEventListener('change', function () {
                renderListaGrupos(gruposCatalogoRaw);
            });
        }
        if (search) {
            search.addEventListener('input', function () {
                renderListaGrupos(gruposCatalogoRaw);
            });
        }
        if (clearBtn) {
            clearBtn.addEventListener('click', limparFiltroGrupos);
        }
        const limparStrip = el('btnLimparGruposStrip');
        if (limparStrip) {
            limparStrip.addEventListener('click', limparFiltroGrupos);
        }
        if (reloadBtn) {
            reloadBtn.addEventListener('click', carregarGruposProduto);
        }
    }

    function bindFilters() {
        ['tipoProdutoFilter', 'excluirAfericaoFilter'].forEach(function (id) {
            const node = el(id);
            if (node) {
                node.addEventListener('change', function () {
                    updateContextoConsulta();
                    updateDashboard();
                });
            }
        });
        const periodoNode = el('periodoFilter');
        if (periodoNode) {
            periodoNode.addEventListener('change', function () {
                updatePeriodoResumo();
                if (isModoPeriodoCustom()) updateDashboard();
            });
        }
        ['dataInicialFilter', 'dataFinalFilter'].forEach(function (id) {
            const node = el(id);
            if (node) {
                node.addEventListener('change', function () {
                    setActiveDatePreset('');
                    updatePeriodoResumo();
                    if (isModoPeriodoCustom()) updateDashboard();
                });
            }
        });
        const filialNode = el('filialFilter');
        if (filialNode) {
            filialNode.addEventListener('change', function () {
                updateContextoConsulta();
                updateDashboard();
            });
            filialNode.addEventListener('keyup', function (ev) {
                if (ev.key === 'Enter') {
                    updateContextoConsulta();
                    updateDashboard();
                }
            });
        }
        const descNode = el('descricaoProdutoFilter');
        if (descNode) {
            descNode.addEventListener('change', carregarProdutosDoPosto);
            descNode.addEventListener('keyup', function (ev) {
                if (ev.key === 'Enter') carregarProdutosDoPosto();
            });
        }
    }

    function initCockpit() {
        resetFiltroGruposNoBoot();
        const input = el('tokenInput');
        if (input) input.value = getToken();
        setModoDadosReais(false, 'Carregando métricas da API WebPosto…');
        bindSidebarNav();
        bindQuickActions();
        bindModoDataConsulta();
        bindDatePresets();
        bindFilters();
        bindPostosPanel();
        bindGruposPanel();
        const btnLimparOverview = el('btnLimparGruposOverview');
        if (btnLimparOverview) btnLimparOverview.addEventListener('click', limparFiltroGrupos);
        initDateFilters();
        renderFilialPills();
        updateContextoConsulta();
        carregarOpcoesProduto();
        checkHealth();
        Promise.all([carregarGruposProduto(), updateDashboard()]).catch(function (e) {
            console.error(e);
        });
    }

    global.applyCockpitToken = applyToken;
    global.applyToken = applyToken;
    global.updateDashboard = updateDashboard;
    global.updateCockpitDashboard = updateDashboard;
    global.initLogosCockpit = initCockpit;
    global.carregarProdutosDoPosto = carregarProdutosDoPosto;
    global.carregarGruposProduto = carregarGruposProduto;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCockpit);
    } else {
        initCockpit();
    }
})(window);
