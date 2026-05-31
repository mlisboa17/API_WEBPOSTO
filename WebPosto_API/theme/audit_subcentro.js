/**
 * Auditoria por sub-centro — período + PISTA | LOJA | FOOD · faturamento R$
 */
(function (global) {
    'use strict';

    const AUDIT_BASE = '/api/v1/audit';

    const SUB_CENTROS = [
        { value: 'PISTA', label: 'Pista (combustível)', hint: 'Faturamento ABASTECIMENTO + litros' },
        { value: 'LOJA', label: 'Loja (conveniência)', hint: 'Faturamento PDV loja · galonagem zero' },
        { value: 'FOOD', label: 'Food', hint: 'Faturamento PDV food · galonagem zero' },
    ];

    function el(id) {
        return document.getElementById(id);
    }

    function fmtReais(n) {
        return (
            'R$ ' +
            Number(n || 0).toLocaleString('pt-BR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            })
        );
    }

    function fmtLitros(n) {
        return (
            Number(n || 0).toLocaleString('pt-BR', { maximumFractionDigits: 0 }) + ' L'
        );
    }

    function getDatas() {
        const di = (el('audit-data-inicial') && el('audit-data-inicial').value) || '';
        const df = (el('audit-data-final') && el('audit-data-final').value) || '';
        return { di, df };
    }

    function auditFilialQuery() {
        const inp = el('filter-filial');
        const raw = (inp && inp.value) || '';
        const s = String(raw).trim();
        return s ? '&filial=' + encodeURIComponent(s) : '';
    }

    function formatApiError(data, status) {
        if (typeof data.detail === 'string') return data.detail;
        if (Array.isArray(data.detail)) {
            return data.detail.map(function (d) {
                return d.msg || JSON.stringify(d);
            }).join('; ');
        }
        return 'Erro HTTP ' + status + ' — sem dados fictícios retornados.';
    }

    function syncDatasFromGlobal() {
        const gDi = el('filter-data-inicial');
        const gDf = el('filter-data-final');
        const aDi = el('audit-data-inicial');
        const aDf = el('audit-data-final');
        if (gDi && gDi.value && aDi && !aDi.value) aDi.value = gDi.value;
        if (gDf && gDf.value && aDf && !aDf.value) aDf.value = gDf.value;
    }

    function validarDatas(di, df) {
        if (!di || !df) {
            throw new Error('Informe data inicial e data final.');
        }
        if (df < di) {
            throw new Error('Data final deve ser igual ou posterior à inicial.');
        }
    }

    function renderHintSubCentro() {
        const sel = el('audit-sub-centro');
        const hint = el('audit-sub-centro-hint');
        if (!sel || !hint) return;
        const sc = SUB_CENTROS.find(function (x) {
            return x.value === sel.value;
        });
        hint.textContent = sc ? sc.hint : '';
    }

    function buildCardHtml(item) {
        const sc = item.sub_centro || '—';
        const alerta = item.alerta_critico
            ? '<p class="audit-alert">⚠ Divergência acima da tolerância operacional</p>'
            : '';
        return (
            '<div class="audit-card">' +
            '<div class="audit-card__head">' +
            '<h4>' +
            sc +
            '</h4>' +
            '<span class="audit-card__badge">' +
            (item.moeda || 'BRL') +
            '</span>' +
            '</div>' +
            '<div class="audit-kpis">' +
            '<div class="audit-kpi audit-kpi--fat"><span>Faturamento período</span><strong>' +
            fmtReais(item.faturamento_periodo) +
            '</strong></div>' +
            '<div class="audit-kpi"><span>Galonagem</span><strong>' +
            fmtLitros(item.galonagem_litros) +
            '</strong></div>' +
            '<div class="audit-kpi"><span>Caixa apurado</span><strong>' +
            fmtReais(item.valor_apurado) +
            '</strong></div>' +
            '<div class="audit-kpi"><span>Caixa apresentado</span><strong>' +
            fmtReais(item.valor_apresentado) +
            '</strong></div>' +
            '<div class="audit-kpi audit-kpi--div"><span>Divergência</span><strong>' +
            fmtReais(item.divergencia) +
            '</strong></div>' +
            '</div>' +
            alerta +
            '<p class="audit-meta">Turnos: ' +
            (item.turnos_totais != null ? item.turnos_totais : '—') +
            '</p>' +
            '</div>'
        );
    }

    function buildCardCompact(item) {
        const sc = item.sub_centro || '—';
        return (
            '<div class="audit-card audit-card--compact">' +
            '<h4 class="audit-card__title">' +
            sc +
            '</h4>' +
            '<p class="audit-card__fat">' +
            fmtReais(item.faturamento_periodo) +
            '</p>' +
            '<p class="audit-card__sub">' +
            fmtLitros(item.galonagem_litros) +
            ' · div. ' +
            fmtReais(item.divergencia) +
            '</p>' +
            '</div>'
        );
    }

    function renderResultadoTres(data) {
        const out = el('audit-resultado');
        if (!out) return;
        let h =
            '<p class="audit-meta">Período ' +
            data.data_inicio +
            ' → ' +
            data.data_fim +
            '</p>';
        h +=
            '<p class="audit-total-posto">Total posto: <strong>' +
            fmtReais(data.faturamento_total_posto) +
            '</strong></p>';
        h += '<div class="audit-grid-tres">';
        (data.itens || []).forEach(function (item) {
            h += buildCardCompact(item);
        });
        h += '</div>';
        out.innerHTML = h;
    }

    async function consultarSubCentro() {
        const { di, df } = getDatas();
        validarDatas(di, df);
        const subCentro = el('audit-sub-centro').value;
        const out = el('audit-resultado');
        const btn = el('audit-btn-consultar');
        if (btn) btn.disabled = true;
        if (out) out.innerHTML = '<p class="audit-loading">Consultando faturamento…</p>';

        try {
            const url =
                AUDIT_BASE + '/faturamento?data_inicio=' +
                encodeURIComponent(di) +
                '&data_fim=' +
                encodeURIComponent(df) +
                auditFilialQuery();
            const r = await fetch(url);
            const data = await r.json();
            if (!r.ok) {
                throw new Error(formatApiError(data, r.status));
            }
            const item = (data.itens || []).find(function (i) {
                return i.sub_centro === subCentro;
            });
            if (item) {
                out.innerHTML = buildCardHtml(item);
                return;
            }
            await consultarReconciliacaoAsync(di, df, subCentro);
        } catch (e) {
            if (out) {
                out.innerHTML =
                    '<p class="audit-error">' + (e.message || String(e)) + '</p>';
            }
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    async function consultarReconciliacaoAsync(di, df, subCentro) {
        const out = el('audit-resultado');
        const proc = await fetch(
            AUDIT_BASE + '/process?data_inicio=' +
                encodeURIComponent(di) +
                '&data_fim=' +
                encodeURIComponent(df) +
                auditFilialQuery() +
                '&sub_centro=' +
                encodeURIComponent(subCentro),
            { method: 'POST' }
        );
        const accepted = await proc.json();
        if (proc.status !== 202) {
            throw new Error(
                typeof accepted.detail === 'string'
                    ? accepted.detail
                    : 'Falha ao enfileirar auditoria'
            );
        }
        const jobId = accepted.job_id;
        if (out) {
            out.innerHTML =
                '<p class="audit-loading">Reconciliando caixa (job ' +
                String(jobId).slice(0, 8) +
                '…)…</p>';
        }
        for (let i = 0; i < 40; i++) {
            await new Promise(function (res) {
                setTimeout(res, 1500);
            });
            const jr = await fetch(AUDIT_BASE + '/jobs/' + jobId);
            const job = await jr.json();
            if (job.status === 'done' && job.result) {
                out.innerHTML = buildCardHtml(job.result);
                return;
            }
            if (job.status === 'failed') {
                throw new Error(job.error || 'Job falhou');
            }
        }
        throw new Error('Tempo esgotado aguardando auditoria.');
    }

    async function consultarTresSubCentros() {
        const { di, df } = getDatas();
        validarDatas(di, df);
        const out = el('audit-resultado');
        const btn = el('audit-btn-todos');
        if (btn) btn.disabled = true;
        if (out) out.innerHTML = '<p class="audit-loading">Carregando PISTA, LOJA e FOOD…</p>';

        try {
            const url =
                AUDIT_BASE + '/faturamento?data_inicio=' +
                encodeURIComponent(di) +
                '&data_fim=' +
                encodeURIComponent(df) +
                auditFilialQuery();
            const r = await fetch(url);
            const data = await r.json();
            if (!r.ok) {
                throw new Error(formatApiError(data, r.status));
            }
            renderResultadoTres(data);
        } catch (e) {
            if (out) {
                out.innerHTML =
                    '<p class="audit-error">' + (e.message || String(e)) + '</p>';
            }
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    function copiarPeriodoGlobal() {
        const gDi = el('filter-data-inicial');
        const gDf = el('filter-data-final');
        const aDi = el('audit-data-inicial');
        const aDf = el('audit-data-final');
        if (gDi && aDi) aDi.value = gDi.value || '';
        if (gDf && aDf) aDf.value = gDf.value || '';
    }

    function initAuditSubCentroView() {
        syncDatasFromGlobal();
        renderHintSubCentro();
        const sel = el('audit-sub-centro');
        if (sel && !sel.dataset.bound) {
            sel.dataset.bound = '1';
            sel.addEventListener('change', renderHintSubCentro);
        }
    }

    global.consultarAuditSubCentro = consultarSubCentro;
    global.consultarAuditTodosSubCentros = consultarTresSubCentros;
    global.copiarPeriodoGlobalParaAudit = copiarPeriodoGlobal;
    global.initAuditSubCentroView = initAuditSubCentroView;
})(window);
