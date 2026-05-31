import React, { useEffect, useState } from 'react'
import api, { setToken, getToken } from './api'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export default function App() {
  const [status, setStatus] = useState('checking')
  const [endpoints, setEndpoints] = useState([])
  const [selected, setSelected] = useState(null)
  const [query, setQuery] = useState('')
  const [body, setBody] = useState('{}')
  const [response, setResponse] = useState(null)
  const [token, setTokenState] = useState(getToken() || '')

  useEffect(() => {
    setEndpoints([
      // Abastecimento
      { method: 'GET', path: '/INTEGRACAO/ABASTECIMENTO', desc: 'Listar abastecimentos', category: 'Abastecimento', params: ['data_inicio (ISO)', 'data_fim (ISO)', 'pagina', 'limite'], sample: null },
      { method: 'GET', path: '/INTEGRACAO/ABASTECIMENTO_DIVERGENCIA', desc: 'Divergências de abastecimento', category: 'Abastecimento', params: ['data_inicio', 'data_fim'], sample: null },
      { method: 'GET', path: '/INTEGRACAO/ABASTECIMENTO_ENCERRANTE', desc: 'Encerrantes de abastecimento', category: 'Abastecimento', params: ['data'], sample: null },

      // Clientes
      { method: 'GET', path: '/INTEGRACAO/CLIENTE', desc: 'Listar clientes', category: 'Clientes', params: ['pagina', 'limite', 'ativo'], sample: null },
      { method: 'GET', path: '/INTEGRACAO/CLIENTE_FROTA', desc: 'Frota por cliente', category: 'Clientes', params: ['cliente_id'], sample: null },
      { method: 'GET', path: '/INTEGRACAO/GRUPO_CLIENTE', desc: 'Grupos de clientes', category: 'Clientes', params: [], sample: null },

      // Financeiro
      { method: 'GET', path: '/INTEGRACAO/TITULO_RECEBER', desc: 'Títulos a receber', category: 'Financeiro', params: ['data_inicio','data_fim','status','cliente_id'], sample: null },
      { method: 'GET', path: '/INTEGRACAO/TITULO_PAGAR', desc: 'Títulos a pagar', category: 'Financeiro', params: ['data_inicio','data_fim','status'], sample: null },
      { method: 'GET', path: '/INTEGRACAO/CAIXA', desc: 'Movimentos de caixa', category: 'Financeiro', params: ['data_inicio','data_fim'], sample: null },
      { method: 'GET', path: '/INTEGRACAO/CAIXA_APRESENTADO', desc: 'Caixa apresentado x apurado', category: 'Financeiro', params: ['data_inicio','data_fim'], sample: null },
      { method: 'GET', path: '/INTEGRACAO/CARTAO_COMPRA', desc: 'Cartões - compras', category: 'Financeiro', params: ['data_inicio','data_fim'], sample: null },
      { method: 'GET', path: '/INTEGRACAO/CARTAO_PAGAR', desc: 'Cartões - a pagar', category: 'Financeiro', params: ['data_inicio','data_fim'], sample: null },
      { method: 'GET', path: '/INTEGRACAO/MOVIMENTO_CONTA', desc: 'Movimento de conta', category: 'Financeiro', params: ['conta_id','data_inicio','data_fim'], sample: null },
      { method: 'GET', path: '/INTEGRACAO/PLANO_DE_CONTAS', desc: 'Plano de contas', category: 'Financeiro', params: [], sample: null },
      { method: 'GET', path: '/INTEGRACAO/FECHAMENTO_CAIXA', desc: 'Fechamentos de caixa', category: 'Financeiro', params: ['data_inicio','data_fim'], sample: null },
      { method: 'GET', path: '/INTEGRACAO/TRANSFERENCIA', desc: 'Transferências', category: 'Financeiro', params: ['data_inicio','data_fim'], sample: null },
      { method: 'GET', path: '/INTEGRACAO/TRANSFERENCIA_BANCARIA', desc: 'Transferências bancárias', category: 'Financeiro', params: ['data_inicio','data_fim'], sample: null },

      // Produtos
      { method: 'GET', path: '/INTEGRACAO/PRODUTO', desc: 'Listar produtos', category: 'Produtos', params: ['pagina','limite','categoria'], sample: null },
      { method: 'GET', path: '/INTEGRACAO/COMBUSTIVEL', desc: 'Combustíveis cadastrados', category: 'Produtos', params: [], sample: null },
      { method: 'GET', path: '/INTEGRACAO/ESTOQUE', desc: 'Posição de estoque', category: 'Produtos', params: ['produto_id'], sample: null },
      { method: 'GET', path: '/INTEGRACAO/PRECO_PRODUTO', desc: 'Preço por produto', category: 'Produtos', params: ['produto_id'], sample: null },
      { method: 'GET', path: '/INTEGRACAO/INTEGRACAO_PRODUTO_TRIBUTO_ICMS', desc: 'Tributo ICMS por produto', category: 'Produtos', params: ['produto_id'], sample: null },
      { method: 'GET', path: '/INTEGRACAO/INTEGRACAO_PRODUTO_TRIBUTO_PIS_CONFINS', desc: 'Tributos PIS/COFINS por produto', category: 'Produtos', params: ['produto_id'], sample: null },

      // Vendas & NF
      { method: 'GET', path: '/INTEGRACAO/VENDA', desc: 'Listar vendas', category: 'Vendas', params: ['data_inicio','data_fim','cliente_id','status'], sample: null },
      { method: 'GET', path: '/INTEGRACAO/NOTA_FISCAL_SAIDA', desc: 'Notas fiscais saída', category: 'Vendas', params: ['data_inicio','data_fim'], sample: null },
      { method: 'GET', path: '/INTEGRACAO/NOTA_FISCAL_ENTRADA', desc: 'Notas fiscais entrada', category: 'Vendas', params: ['data_inicio','data_fim'], sample: null },
      { method: 'GET', path: '/INTEGRACAO/VENDA_REDE', desc: 'Vendas consolidadas (rede)', category: 'Vendas', params: ['data_inicio','data_fim'], sample: null },
      { method: 'GET', path: '/INTEGRACAO/PEDIDO_COMPRAS', desc: 'Pedidos de compras', category: 'Vendas', params: ['status'], sample: null },
      { method: 'GET', path: '/INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO', desc: 'Pedidos de combustível', category: 'Vendas', params: ['status'], sample: null },

      // Relatórios
      { method: 'GET', path: '/INTEGRACAO/RELATORIO/ESTOQUE', desc: 'Relatório de estoque', category: 'Relatórios', params: ['data_inicio','data_fim'], sample: null },
      { method: 'GET', path: '/INTEGRACAO/RELATORIO/VENDA_COMBUSTIVEL', desc: 'Relatório venda combustível', category: 'Relatórios', params: ['data_inicio','data_fim'], sample: null },
      { method: 'GET', path: '/INTEGRACAO/RELATORIO/VENDA_PRODUTO', desc: 'Relatório venda produto', category: 'Relatórios', params: ['data_inicio','data_fim'], sample: null },
      { method: 'GET', path: '/INTEGRACAO/RELATORIO/RESUMO_VENDAS', desc: 'Resumo de vendas', category: 'Relatórios', params: ['data_inicio','data_fim'], sample: null },

      // Administração
      { method: 'GET', path: '/INTEGRACAO/USUARIO', desc: 'Listar usuários', category: 'Administração', params: [], sample: null },
      { method: 'GET', path: '/INTEGRACAO/FILIAL', desc: 'Listar filiais', category: 'Administração', params: [], sample: null },
      { method: 'GET', path: '/INTEGRACAO/ADMINISTRADORA', desc: 'Administradoras de cartão', category: 'Administração', params: [], sample: null },

      // Auditoria / Internos
      { method: 'GET', path: '/auditoria/registros', desc: 'Registros de auditoria', category: 'Auditoria', params: ['filtro_tabela','filtro_registro_id'], sample: null },
      // Sync/internal helpers
      { method: 'GET', path: '/sync/status', desc: 'Status de sincronização (interno)', category: 'Sistema', params: [], sample: null },
    ])

    checkHealth()
  }, [])

  const checkHealth = async () => {
    try {
      const res = await api.get('/health')
      setStatus(res.status === 200 ? 'online' : 'offline')
    } catch (e) {
      setStatus('offline')
    }
  }

  const saveToken = () => {
    setToken(token || null)
    setTokenState(token)
  }

  const clearToken = () => {
    setToken(null)
    setTokenState('')
  }

  const sendRequest = async () => {
    if (!selected) return
    setResponse({ loading: true })

    try {
      const url = `${selected.path}${query ? `?${query}` : ''}`
      const payload = (selected.method === 'POST' || selected.method === 'PUT') ? JSON.parse(body) : undefined

      const res = await api.request({ url, method: selected.method, data: payload })
      setResponse({ status: res.status, data: res.data })
    } catch (err) {
      setResponse({ error: err.message, details: err.response?.data })
    }
  }

  return (
    <div className="rv-container">
      <aside className="rv-sidebar">
        <h2>WebPosto</h2>
        <div className="rv-status">API: <strong>{status}</strong></div>

        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 12, color: '#9fb3d6' }}>Token (opcional)</label>
          <input
            style={{ width: '100%', padding: 6, borderRadius: 6, border: '1px solid #233444' }}
            value={token}
            onChange={e => setTokenState(e.target.value)}
            placeholder="cole o token aqui"
          />
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <button className="btn" onClick={saveToken} style={{ flex: 1 }}>Salvar token</button>
            <button className="btn" onClick={clearToken} style={{ flex: 1, background: '#e2e8f0', color: '#0f172a' }}>Limpar</button>
          </div>
        </div>

        <div className="rv-list">
          {endpoints.map((ep, i) => (
            <button key={i} className={`rv-ep ${selected === ep ? 'active' : ''}`} onClick={() => setSelected(ep)}>
              <span className={`badge ${ep.method}`}>{ep.method}</span>
              <div className="rv-ep-info">
                <div className="rv-ep-desc">{ep.desc}</div>
                <div className="rv-ep-path">{ep.path}</div>
              </div>
            </button>
          ))}
        </div>
      </aside>

      <main className="rv-main">
        <header>
          <h1>Explorer</h1>
          <p>Base URL: {API_BASE}</p>
        </header>

        <section className="rv-panel">
          <h3>Teste</h3>
          {selected ? (
            <div>
              <div className="field"><label>Método</label><input value={selected.method} disabled/></div>
              <div className="field"><label>Endpoint</label><input value={selected.path} disabled/></div>
              <div className="field"><label>Query</label><input value={query} onChange={e => setQuery(e.target.value)} placeholder="limit=10"/></div>
              {selected?.params && selected.params.length > 0 && (
                <div className="field">
                  <label>Parâmetros esperados</label>
                  <div style={{ fontSize: 12, color: '#6b7280' }}>{selected.params.join(', ')}</div>
                </div>
              )}
              {(selected.method === 'POST' || selected.method === 'PUT') && (
                <div className="field"><label>Body (JSON)</label><textarea value={body} onChange={e => setBody(e.target.value)} /></div>
              )}
              {(selected.method === 'POST' || selected.method === 'PUT') && selected.sample && (
                <div style={{ marginTop: 8 }}>
                  <button className="btn" onClick={() => setBody(JSON.stringify(selected.sample, null, 2))}>Inserir exemplo</button>
                </div>
              )}
              <button className="btn" onClick={sendRequest}>Enviar</button>
            </div>
          ) : <div>Selecione um endpoint</div>}
        </section>

        <section className="rv-panel">
          <h3>Resposta</h3>
          <pre className="rv-response">{response ? (response.loading ? 'Enviando...' : JSON.stringify(response, null, 2)) : 'Sem resposta'}</pre>
        </section>
      </main>
    </div>
  )
}
