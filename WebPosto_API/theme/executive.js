/**
 * Lionda Executive Shell — proxy WebPosto, CHAVE e KPIs.
 */
(function (global) {
    'use strict';

    const STORAGE_KEY = 'WEBPOSTO_CHAVE';
    const PROXY_URL = '/api/webposto/proxy';
    const CONFIG_URL = '/api/config';
    const INVALID_KEYS = new Set(['', 'SEU_TOKEN_AQUI', '__from_env__', 'sua_chave_api_rest_aqui']);

    function sanitizeChave(v) {
        const s = String(v || '').trim();
        return INVALID_KEYS.has(s) ? '' : s;
    }

    /** Chave digitada pelo usuário (localStorage). Vazio = servidor usa .env */
    function getChave() {
        return sanitizeChave(global.localStorage.getItem(STORAGE_KEY));
    }

    function setChave(value) {
        const v = sanitizeChave(value);
        if (v) global.localStorage.setItem(STORAGE_KEY, v);
        else global.localStorage.removeItem(STORAGE_KEY);
        syncChaveInput();
    }

    function syncChaveInput() {
        const el = document.getElementById('lionda-chave-input');
        const hint = document.getElementById('lionda-chave-hint');
        const k = getChave();
        if (el && document.activeElement !== el) {
            el.value = k;
            el.type = k ? 'password' : 'text';
        }
        if (hint && !global.__WP_HINT_FROM_SERVER__) {
            hint.textContent = k
                ? 'CHAVE salva neste navegador'
                : 'Sem CHAVE local — o servidor usará WEBPOSTO_API_KEY do .env';
        }
    }

    function wpErrorDetail(r) {
        if (!r || r.ok) return '';
        const b = r._body;
        if (b == null) return '';
        if (typeof b === 'string') return b.slice(0, 400);
        if (typeof b === 'object') {
            if (b.message) return String(b.message);
            if (b.error) return String(b.error);
            if (b.detail) return String(b.detail);
            try {
                return JSON.stringify(b).slice(0, 400);
            } catch (_) {
                return '';
            }
        }
        return String(b).slice(0, 400);
    }

    async function loadConfigFromServer() {
        const hint = document.getElementById('lionda-chave-hint');
        try {
            const r = await fetch(CONFIG_URL);
            if (!r.ok) {
                if (hint) {
                    hint.textContent =
                        'Servidor offline? Rode: python src/presentation/app.py';
                }
                return;
            }
            const cfg = await r.json();
            global.__WP_HINT_FROM_SERVER__ = true;
            if (hint) {
                if (cfg.has_key && cfg.key_hint) {
                    hint.textContent =
                        '✅ Chave no .env (' +
                        cfg.key_hint +
                        ')' +
                        (getChave() ? ' · você também tem CHAVE local' : ' — pronta para consultas');
                } else if (cfg.has_key) {
                    hint.textContent = '✅ Chave configurada no .env do servidor';
                } else {
                    hint.textContent =
                        '⚠️ Sem chave no .env — cole a CHAVE WebPosto abaixo e clique Salvar';
                }
            }
            try {
                const hr = await fetch('/api/health/webposto');
                const h = await hr.json();
                if (h && h.ok === true && hint) {
                    hint.textContent =
                        '✅ Chave validada (' +
                        (h.endpoint_testado || 'EMPRESAS') +
                        ', HTTP ' +
                        h.status_code +
                        ')' +
                        (getChave() ? ' · CHAVE local também definida' : '');
                } else if (h && h.ok === false && hint) {
                    const st = h.status_code || '?';
                    hint.innerHTML =
                        '<strong style="color:#ff5252">⚠️ CHAVE do .env rejeitada (HTTP ' +
                        st +
                        ').</strong> Gere uma nova chave no WebPosto (Administração → Integrações) e atualize WEBPOSTO_API_KEY no arquivo .env, depois reinicie o servidor.';
                    if (typeof global.mostrarMensagem === 'function') {
                        global.mostrarMensagem(
                            'CHAVE inválida ou expirada (HTTP ' +
                                st +
                                '). Atualize o .env e reinicie: python src/presentation/app.py',
                            'error'
                        );
                    }
                }
            } catch (_) { /* ignore */ }
        } catch (_) {
            if (hint) {
                hint.textContent =
                    'Não conectou ao servidor. Use http://127.0.0.1:8765/ (não abra o .html direto).';
            }
        }
    }

    async function wpFetch(urlOrString, init) {
        if (global.location.protocol === 'file:') {
            throw new Error(
                'Abra o dashboard em http://127.0.0.1:8765/ — execute: python src/presentation/app.py'
            );
        }

        const url = new URL(urlOrString.toString(), global.location.origin);
        const path = url.pathname;
        const query = {};
        url.searchParams.forEach(function (v, k) {
            if (k !== 'CHAVE') query[k] = v;
        });

        const fromUrl = sanitizeChave(url.searchParams.get('CHAVE'));
        const chave = fromUrl || getChave();
        const method = (init && init.method) || 'GET';

        const r = await fetch(PROXY_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
            body: JSON.stringify({
                path: path,
                query: query,
                chave: chave || undefined,
                method: method,
                use_cache: method === 'GET',
            }),
            credentials: 'same-origin',
        });

        let envelope;
        try {
            envelope = await r.json();
        } catch (e) {
            throw new Error('Resposta inválida do proxy: ' + e.message);
        }

        if (envelope.detail && !envelope.status_code) {
            throw new Error(envelope.detail);
        }

        const status = envelope.status_code != null ? envelope.status_code : r.status;
        const ok = status >= 200 && status < 300;

        const response = {
            ok: ok,
            status: status,
            headers: {
                get: function (name) {
                    if (name && name.toLowerCase() === 'content-type') {
                        return envelope.content_type || 'application/json';
                    }
                    return null;
                },
            },
            json: async function () {
                return envelope.body;
            },
            text: async function () {
                return typeof envelope.body === 'string'
                    ? envelope.body
                    : JSON.stringify(envelope.body);
            },
            _body: envelope.body,
            _elapsed_ms: envelope.elapsed_ms,
            _cache_hit: envelope.cache_hit,
        };

        return response;
    }

    function wpHttpError(label, r) {
        const extra = wpErrorDetail(r);
        let msg = label + ' HTTP ' + (r && r.status);
        if (r && r.status === 401) {
            msg += ' — CHAVE inválida ou expirada. Atualize o .env ou o campo CHAVE acima.';
        } else if (r && r.status === 403) {
            msg += ' — sem permissão para este endpoint/filial.';
        } else if (r && r.status === 400) {
            msg += ' — parâmetros inválidos ou CHAVE incorreta.';
        }
        if (extra) msg += ' Detalhe: ' + extra;
        return msg;
    }

    function initLiondaShell() {
        if (global.location.protocol === 'file:') {
            const bar = document.getElementById('lionda-chave-bar');
            if (bar) {
                bar.style.borderColor = '#ff5252';
            }
        }

        const btn = document.getElementById('lionda-chave-save');
        const input = document.getElementById('lionda-chave-input');

        syncChaveInput();
        loadConfigFromServer();

        if (btn) {
            btn.addEventListener('click', function () {
                setChave(input ? input.value : '');
                loadConfigFromServer();
                if (typeof global.mostrarMensagem === 'function') {
                    global.mostrarMensagem(
                        getChave()
                            ? 'CHAVE salva. Clique em Carregar relatório ativo.'
                            : 'CHAVE removida — usando .env do servidor.',
                        'success'
                    );
                }
            });
        }
        if (input) {
            input.addEventListener('keydown', function (e) {
                if (e.key === 'Enter') btn && btn.click();
            });
        }
    }

    global.wpFetch = wpFetch;
    global.wpErrorDetail = wpErrorDetail;
    global.wpHttpError = wpHttpError;
    global.getWebPostoChave = getChave;
    global.setWebPostoChave = setChave;
    global.initLiondaShell = initLiondaShell;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initLiondaShell);
    } else {
        initLiondaShell();
    }
})(window);
