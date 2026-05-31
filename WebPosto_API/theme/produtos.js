/**
 * CRUD de produtos WebPosto — filtros ativo/inativo, multi-grupo, preço A e custo.
 */
(function (global) {
    'use strict';

    let pagina = 1;
    const limite = 30;
    let grupos = [];
    let editandoId = null;

    function el(id) {
        return document.getElementById(id);
    }

    function setStatus(msg, ok) {
        const bar = el('statusBar');
        if (!bar) return;
        bar.textContent = msg;
        bar.className = ok ? 'omie-status-bar omie-status-bar--ok' : 'omie-status-bar omie-status-bar--warn';
    }

    function pick(obj, snake, camel) {
        if (!obj) return undefined;
        var v = obj[snake];
        if (v !== undefined && v !== null && v !== '') return v;
        return obj[camel];
    }

    function precoVenda(p) {
        return pick(p, 'preco_venda', 'precoVenda');
    }

    function precoCusto(p) {
        return pick(p, 'preco_custo', 'precoCusto');
    }

    function fmtBRL(n) {
        return (
            'R$ ' +
            Number(n || 0).toLocaleString('pt-BR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 4,
            })
        );
    }

    function getGruposSelecionados() {
        const list = el('filtroGruposList');
        if (!list) return [];
        const out = [];
        list.querySelectorAll('input[type=checkbox][data-grupo-codigo]:checked').forEach(function (cb) {
            out.push(String(cb.getAttribute('data-grupo-codigo')));
        });
        return out;
    }

    function atualizarResumoGrupos() {
        const summary = el('gruposResumo');
        if (!summary) return;
        const sel = getGruposSelecionados();
        if (!sel.length) {
            summary.textContent = grupos.length + ' grupo(s) · nenhum filtro de grupo (mostra todos)';
            return;
        }
        const nomes = grupos
            .filter(function (g) {
                return sel.indexOf(String(g.codigo)) >= 0;
            })
            .map(function (g) {
                return g.nome;
            });
        summary.textContent =
            sel.length +
            ' grupo(s): ' +
            nomes.slice(0, 4).join(', ') +
            (nomes.length > 4 ? '…' : '');
    }

    function renderGruposFiltro() {
        const list = el('filtroGruposList');
        const selForm = el('grupoCodigo');
        if (!list) return;

        list.innerHTML = '';
        grupos.forEach(function (g) {
            const cod = String(g.codigo);
            const label = document.createElement('label');
            label.className = 'grupo-chip';
            label.innerHTML =
                '<input type="checkbox" data-grupo-codigo="' +
                cod +
                '">' +
                '<span>' +
                (g.nome || 'Grupo ' + cod) +
                ' <span class="text-gray-600">(' +
                cod +
                ')</span></span>';
            const cb = label.querySelector('input');
            cb.addEventListener('change', atualizarResumoGrupos);
            list.appendChild(label);
        });

        if (selForm) {
            selForm.innerHTML = '';
            grupos.forEach(function (g) {
                const opt = document.createElement('option');
                opt.value = String(g.codigo);
                opt.textContent = (g.nome || 'Grupo') + ' (' + g.codigo + ')';
                selForm.appendChild(opt);
            });
        }
        atualizarResumoGrupos();
    }

    async function carregarGrupos() {
        try {
            const res = await fetch('/api/v1/webposto/grupos-produto');
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Falha grupos');
            grupos = data.grupos || [];
            renderGruposFiltro();
            if (data.unidade && data.unidade.fantasia) {
                setStatus('API · ' + data.unidade.fantasia, true);
            }
        } catch (e) {
            setStatus('Grupos: ' + e.message, false);
        }
    }

    async function listarProdutos() {
        const tbody = el('tabelaProdutos');
        const desc = (el('filtroDescricao') && el('filtroDescricao').value) || '';
        const situacao = (el('filtroSituacao') && el('filtroSituacao').value) || 'todos';
        const gruposSel = getGruposSelecionados();

        const params = new URLSearchParams({
            pagina: String(pagina),
            limite: String(limite),
            situacao: situacao,
        });
        if (desc) params.set('descricao', desc);
        if (gruposSel.length) params.set('grupos', gruposSel.join(','));

        if (tbody) {
            tbody.innerHTML =
                '<tr><td colspan="8" class="p-6 text-center text-gray-500">Carregando…</td></tr>';
        }

        try {
            const res = await fetch('/api/v1/webposto/produtos?' + params.toString());
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Erro ' + res.status);

            const info = el('paginacaoInfo');
            if (info) {
                info.textContent =
                    'Página ' +
                    data.pagina_atual +
                    ' / ' +
                    data.total_paginas +
                    ' · ' +
                    data.total_registros +
                    ' registro(s) · ' +
                    situacao;
            }
            el('btnPagAnterior').disabled = pagina <= 1;
            el('btnPagProxima').disabled = pagina >= (data.total_paginas || 1);

            if (!data.produtos || !data.produtos.length) {
                tbody.innerHTML =
                    '<tr><td colspan="8" class="p-6 text-center text-gray-600">Nenhum produto no filtro</td></tr>';
                return;
            }

            tbody.innerHTML = '';
            data.produtos.forEach(function (p) {
                const ativo = p.ativo !== false;
                const tr = document.createElement('tr');
                tr.innerHTML =
                    '<td class="omie-cell-code">' +
                    p.id +
                    '</td><td>' +
                    (p.descricao || '') +
                    '</td><td class="text-gray-500">' +
                    (pick(p, 'nome_grupo', 'nomeGrupo') || pick(p, 'codigo_grupo', 'codigoGrupo') || '—') +
                    '</td><td class="' +
                    (ativo ? 'badge-ativo' : 'badge-inativo') +
                    '">' +
                    (ativo ? 'Ativo' : 'Inativo') +
                    '</td><td class="text-right omie-cell-money">' +
                    fmtBRL(precoVenda(p)) +
                    '</td><td class="text-right omie-cell-cost">' +
                    fmtBRL(precoCusto(p)) +
                    '</td><td>' +
                    (p.ncm || '—') +
                    '</td><td class="text-right"><button type="button" data-edit="' +
                    p.id +
                    '" class="omie-table-link">Editar</button></td>';
                tbody.appendChild(tr);
            });

            tbody.querySelectorAll('[data-edit]').forEach(function (btn) {
                btn.addEventListener('click', function () {
                    abrirEdicao(parseInt(btn.getAttribute('data-edit'), 10));
                });
            });

            setStatus('Lista OK · preços via PRODUTO + PRODUTO_EMPRESA', true);
        } catch (e) {
            setStatus(e.message, false);
            if (tbody) {
                tbody.innerHTML =
                    '<tr><td colspan="8" class="p-6 text-center text-red-400">' +
                    e.message +
                    '</td></tr>';
            }
        }
    }

    function payloadForm() {
        return {
            descricao: el('descricao').value.trim(),
            descricaoResumida: el('descricaoResumida').value.trim() || undefined,
            tipoProduto: el('tipoProduto').value,
            grupoCodigo: parseInt(el('grupoCodigo').value, 10),
            precoVenda: parseFloat(el('precoVenda').value) || 0,
            precoCusto: parseFloat(el('precoCusto').value) || 0,
            precoCompra: parseFloat(el('precoCusto').value) || 0,
            unidadeCompra: el('unidadeVenda').value || 'UN',
            unidadeVenda: el('unidadeVenda').value || 'UN',
            codigoBarras: el('codigoBarras').value.trim() || undefined,
            codigoNcm: el('codigoNcm').value.trim() || '00000000',
            ativo: el('ativo').checked,
            tributoIcms: {
                cstSaida: el('cstSaida').value || '060',
                percentualIcmsSaida: 0,
                cstEntrada: '060',
                percentualIcmsEntrada: 0,
            },
        };
    }

    function mostrarForm(novo) {
        const painel = el('painelForm');
        if (painel) painel.classList.remove('hidden');
        el('formTitulo').textContent = novo ? 'Novo produto' : 'Editar produto #' + editandoId;
        painel.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function limparForm() {
        editandoId = null;
        el('produtoId').value = '';
        el('formProduto').reset();
        el('unidadeVenda').value = 'UN';
        el('codigoNcm').value = '00000000';
        el('cstSaida').value = '060';
        el('ativo').checked = true;
        el('painelForm').classList.add('hidden');
    }

    async function abrirEdicao(id) {
        editandoId = id;
        setStatus('Carregando produto ' + id + '…', true);
        el('painelForm').classList.add('hidden');
        try {
            const res = await fetch('/api/v1/webposto/produtos/' + id);
            const p = await res.json();
            if (!res.ok) {
                const d = p.detail;
                throw new Error(typeof d === 'string' ? d : 'Produto não encontrado (HTTP ' + res.status + ')');
            }
            el('produtoId').value = String(p.id);
            el('descricao').value = p.descricao || '';
            el('tipoProduto').value = p.combustivel ? 'C' : 'P';
            var grupo = pick(p, 'codigo_grupo', 'codigoGrupo');
            if (grupo) el('grupoCodigo').value = String(grupo);
            el('precoVenda').value = precoVenda(p) || 0;
            el('precoCusto').value = precoCusto(p) != null ? precoCusto(p) : 0;
            el('codigoBarras').value = pick(p, 'codigo_barra', 'codigoBarras') || '';
            el('codigoNcm').value = p.ncm || '00000000';
            var cst = pick(p, 'cst_icms', 'cstIcms') || '060';
            el('cstSaida').value = String(cst).replace(/^0+/, '').padStart(3, '0');
            el('ativo').checked = p.ativo !== false;
            mostrarForm(false);
            setStatus(
                'Editando: ' +
                    (p.descricao || '#' + id) +
                    ' · venda ' +
                    fmtBRL(precoVenda(p)) +
                    ' · custo ' +
                    fmtBRL(precoCusto(p)),
                true
            );
        } catch (e) {
            editandoId = null;
            setStatus('Erro ao abrir edição: ' + e.message, false);
        }
    }

    async function salvar() {
        const payload = payloadForm();
        const debug = el('formDebug');
        if (debug) {
            debug.classList.remove('hidden');
            debug.textContent = JSON.stringify(payload, null, 2);
        }

        try {
            let res;
            if (editandoId) {
                res = await fetch('/api/v1/webposto/produtos/' + editandoId, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
            } else {
                res = await fetch('/api/v1/webposto/produtos', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
            }
            const data = await res.json();
            if (!res.ok) {
                const d = data.detail;
                throw new Error(typeof d === 'string' ? d : JSON.stringify(d));
            }
            setStatus(data.mensagem || 'Salvo com sucesso', true);
            limparForm();
            listarProdutos();
        } catch (e) {
            setStatus('Erro ao salvar: ' + e.message, false);
        }
    }

    function bind() {
        el('btnBuscar').addEventListener('click', function () {
            pagina = 1;
            listarProdutos();
        });
        el('filtroSituacao').addEventListener('change', function () {
            pagina = 1;
            listarProdutos();
        });
        el('btnPagAnterior').addEventListener('click', function () {
            if (pagina > 1) {
                pagina--;
                listarProdutos();
            }
        });
        el('btnPagProxima').addEventListener('click', function () {
            pagina++;
            listarProdutos();
        });
        el('btnNovo').addEventListener('click', function () {
            editandoId = null;
            limparForm();
            mostrarForm(true);
        });
        el('btnCancelar').addEventListener('click', limparForm);
        el('btnSalvar').addEventListener('click', salvar);
        el('filtroDescricao').addEventListener('keydown', function (ev) {
            if (ev.key === 'Enter') {
                pagina = 1;
                listarProdutos();
            }
        });
        el('gruposMarcarTodos').addEventListener('click', function () {
            const list = el('filtroGruposList');
            if (!list) return;
            list.querySelectorAll('input[type=checkbox]').forEach(function (cb) {
                cb.checked = true;
            });
            atualizarResumoGrupos();
        });
        el('gruposLimpar').addEventListener('click', function () {
            const list = el('filtroGruposList');
            if (!list) return;
            list.querySelectorAll('input[type=checkbox]').forEach(function (cb) {
                cb.checked = false;
            });
            atualizarResumoGrupos();
            pagina = 1;
            listarProdutos();
        });
    }

    function init() {
        bind();
        carregarGrupos().then(listarProdutos);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})(window);
