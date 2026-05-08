import React, { useState, useEffect } from 'react';
import { AlertCircle, Trash2, Edit2, Plus, RefreshCw, Eye, LogOut } from 'lucide-react';

/**
 * Dashboard Administrativo — webPosto API
 * Gerenciamento CRUD de Financeiro, Caixa e Auditoria
 *
 * Funcionalidades:
 * - Listar, criar, editar, deletar títulos
 * - Listar, criar, editar, deletar movimentos de caixa
 * - Visualizar logs de auditoria
 * - Filtros e paginação
 */

export default function Dashboard() {
  const [tab, setTab] = useState('financeiro');
  const [usuario, setUsuario] = useState('gerente');
  const [financeiros, setFinanceiros] = useState([]);
  const [caixas, setCaixas] = useState([]);
  const [auditorias, setAuditorias] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [filtros, setFiltros] = useState({});
  const [paginacao, setPaginacao] = useState({ pagina: 1, limite: 50 });

  // ===============================================
  // API BASE URL
  // ===============================================

  const API_URL = 'http://localhost:5000/api/v1';

  // ===============================================
  // FETCH FUNCTIONS
  // ===============================================

  const fetchFinanceiro = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        pagina: paginacao.pagina,
        limite: paginacao.limite,
        ...filtros
      });
      const res = await fetch(`${API_URL}/financeiro?${params}`);
      const data = await res.json();
      setFinanceiros(data.dados || []);
    } catch (error) {
      console.error('Erro ao buscar financeiro:', error);
    }
    setLoading(false);
  };

  const fetchCaixa = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        pagina: paginacao.pagina,
        limite: paginacao.limite,
        ...filtros
      });
      const res = await fetch(`${API_URL}/caixa?${params}`);
      const data = await res.json();
      setCaixas(data.dados || []);
    } catch (error) {
      console.error('Erro ao buscar caixa:', error);
    }
    setLoading(false);
  };

  const fetchAuditoria = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        pagina: paginacao.pagina,
        limite: paginacao.limite,
        ...filtros
      });
      const res = await fetch(`${API_URL}/auditoria?${params}`);
      const data = await res.json();
      setAuditorias(data.dados || []);
    } catch (error) {
      console.error('Erro ao buscar auditoria:', error);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (tab === 'financeiro') fetchFinanceiro();
    else if (tab === 'caixa') fetchCaixa();
    else if (tab === 'auditoria') fetchAuditoria();
  }, [tab, paginacao]);

  // ===============================================
  // CRUD OPERATIONS
  // ===============================================

  const handleCriarFinanceiro = async (formData) => {
    try {
      const res = await fetch(`${API_URL}/financeiro`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Usuario': usuario,
          'X-Motivo': 'Criação via Web Dashboard'
        },
        body: JSON.stringify(formData)
      });
      if (res.ok) {
        fetchFinanceiro();
        setShowForm(false);
      }
    } catch (error) {
      console.error('Erro ao criar:', error);
    }
  };

  const handleAtualizarFinanceiro = async (id, formData) => {
    try {
      const res = await fetch(`${API_URL}/financeiro/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-Usuario': usuario,
          'X-Motivo': 'Atualização via Web Dashboard'
        },
        body: JSON.stringify(formData)
      });
      if (res.ok) {
        fetchFinanceiro();
        setEditingId(null);
      }
    } catch (error) {
      console.error('Erro ao atualizar:', error);
    }
  };

  const handleDeletarFinanceiro = async (id) => {
    if (!confirm('Tem certeza que quer deletar este título?')) return;
    try {
      const res = await fetch(`${API_URL}/financeiro/${id}`, {
        method: 'DELETE',
        headers: {
          'X-Usuario': usuario,
          'X-Motivo': 'Deleção via Web Dashboard'
        }
      });
      if (res.ok) {
        fetchFinanceiro();
      }
    } catch (error) {
      console.error('Erro ao deletar:', error);
    }
  };

  // ===============================================
  // COMPONENTES
  // ===============================================

  const FormFinanceiro = ({ onSubmit, defaultData = null }) => {
    const [data, setData] = useState(defaultData || {
      tipo: 'RECEBER',
      valor: '',
      data_vencimento: '',
      descricao: '',
      cliente_fornecedor: '',
      categoria: 'Vendas'
    });

    const handleChange = (e) => {
      setData({ ...data, [e.target.name]: e.target.value });
    };

    const handleSubmit = (e) => {
      e.preventDefault();
      onSubmit(data);
    };

    return (
      <form onSubmit={handleSubmit} className="space-y-4 bg-gray-50 p-4 rounded-lg">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Tipo</label>
            <select
              name="tipo"
              value={data.tipo}
              onChange={handleChange}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="RECEBER">Receber</option>
              <option value="PAGAR">Pagar</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Valor</label>
            <input
              type="number"
              name="valor"
              value={data.valor}
              onChange={handleChange}
              step="0.01"
              placeholder="0.00"
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Vencimento</label>
            <input
              type="datetime-local"
              name="data_vencimento"
              value={data.data_vencimento}
              onChange={handleChange}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Categoria</label>
            <input
              type="text"
              name="categoria"
              value={data.categoria}
              onChange={handleChange}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Descrição</label>
          <input
            type="text"
            name="descricao"
            value={data.descricao}
            onChange={handleChange}
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Cliente/Fornecedor</label>
          <input
            type="text"
            name="cliente_fornecedor"
            value={data.cliente_fornecedor}
            onChange={handleChange}
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            required
          />
        </div>

        <div className="flex gap-2">
          <button
            type="submit"
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
          >
            Salvar
          </button>
          <button
            type="button"
            onClick={() => setShowForm(false)}
            className="bg-gray-400 text-white px-4 py-2 rounded-md hover:bg-gray-500"
          >
            Cancelar
          </button>
        </div>
      </form>
    );
  };

  const TabFinanceiro = () => (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">Títulos Financeiros</h2>
        <button
          onClick={() => setShowForm(true)}
          className="bg-green-600 text-white px-4 py-2 rounded-md flex items-center gap-2 hover:bg-green-700"
        >
          <Plus size={18} /> Novo Título
        </button>
      </div>

      {showForm && (
        <FormFinanceiro onSubmit={handleCriarFinanceiro} />
      )}

      <div className="overflow-x-auto">
        <table className="w-full border-collapse border border-gray-300">
          <thead className="bg-gray-200">
            <tr>
              <th className="border px-4 py-2 text-left">ID</th>
              <th className="border px-4 py-2 text-left">Tipo</th>
              <th className="border px-4 py-2 text-right">Valor</th>
              <th className="border px-4 py-2">Vencimento</th>
              <th className="border px-4 py-2">Descrição</th>
              <th className="border px-4 py-2">Status</th>
              <th className="border px-4 py-2">Ações</th>
            </tr>
          </thead>
          <tbody>
            {financeiros.map((titulo) => (
              <tr key={titulo.id} className="hover:bg-gray-50">
                <td className="border px-4 py-2 font-mono text-sm">{titulo.id}</td>
                <td className="border px-4 py-2">
                  <span className={`px-2 py-1 rounded text-white text-sm ${
                    titulo.tipo === 'RECEBER' ? 'bg-green-600' : 'bg-red-600'
                  }`}>
                    {titulo.tipo}
                  </span>
                </td>
                <td className="border px-4 py-2 text-right font-mono">
                  R$ {parseFloat(titulo.valor || 0).toFixed(2)}
                </td>
                <td className="border px-4 py-2 text-sm">
                  {new Date(titulo.data_vencimento).toLocaleDateString('pt-BR')}
                </td>
                <td className="border px-4 py-2 text-sm">{titulo.descricao}</td>
                <td className="border px-4 py-2">
                  <span className={`px-2 py-1 rounded text-white text-xs ${
                    titulo.status === 'pago' ? 'bg-blue-600' :
                    titulo.status === 'vencido' ? 'bg-yellow-600' :
                    'bg-gray-600'
                  }`}>
                    {titulo.status}
                  </span>
                </td>
                <td className="border px-4 py-2 flex gap-2">
                  <button
                    onClick={() => setEditingId(titulo.id)}
                    className="text-blue-600 hover:text-blue-800"
                    title="Editar"
                  >
                    <Edit2 size={18} />
                  </button>
                  <button
                    onClick={() => handleDeletarFinanceiro(titulo.id)}
                    className="text-red-600 hover:text-red-800"
                    title="Deletar"
                  >
                    <Trash2 size={18} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {loading && <p className="text-center text-gray-500">Carregando...</p>}

      <div className="flex justify-between items-center mt-4">
        <button
          onClick={() => setPaginacao({ ...paginacao, pagina: Math.max(1, paginacao.pagina - 1) })}
          className="px-4 py-2 bg-gray-300 rounded hover:bg-gray-400"
        >
          ← Anterior
        </button>
        <span className="text-sm text-gray-600">Página {paginacao.pagina}</span>
        <button
          onClick={() => setPaginacao({ ...paginacao, pagina: paginacao.pagina + 1 })}
          className="px-4 py-2 bg-gray-300 rounded hover:bg-gray-400"
        >
          Próxima →
        </button>
      </div>
    </div>
  );

  const TabAuditoria = () => (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">Log de Auditoria</h2>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead className="bg-gray-200">
            <tr>
              <th className="border px-4 py-2 text-left">ID</th>
              <th className="border px-4 py-2">Tabela</th>
              <th className="border px-4 py-2">Record ID</th>
              <th className="border px-4 py-2">Operação</th>
              <th className="border px-4 py-2">Usuário</th>
              <th className="border px-4 py-2">Data</th>
              <th className="border px-4 py-2">Motivo</th>
            </tr>
          </thead>
          <tbody>
            {auditorias.map((log) => (
              <tr key={log.id} className="hover:bg-gray-50">
                <td className="border px-4 py-2 font-mono">{log.id}</td>
                <td className="border px-4 py-2">
                  <span className="px-2 py-1 bg-blue-100 rounded text-xs">{log.tabela}</span>
                </td>
                <td className="border px-4 py-2 font-mono text-xs">{log.record_id}</td>
                <td className="border px-4 py-2">
                  <span className={`px-2 py-1 rounded text-white text-xs ${
                    log.operacao === 'CREATE' ? 'bg-green-600' :
                    log.operacao === 'UPDATE' ? 'bg-blue-600' :
                    'bg-red-600'
                  }`}>
                    {log.operacao}
                  </span>
                </td>
                <td className="border px-4 py-2 text-sm">{log.usuario}</td>
                <td className="border px-4 py-2 text-xs">
                  {new Date(log.data_operacao).toLocaleString('pt-BR')}
                </td>
                <td className="border px-4 py-2 text-xs text-gray-600">{log.motivo}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {loading && <p className="text-center text-gray-500">Carregando...</p>}
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-700 to-blue-900 text-white shadow-lg">
        <div className="container mx-auto px-4 py-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold">webPosto Admin</h1>
              <p className="text-blue-100">Gerenciamento de Financeiro, Caixa e Auditoria</p>
            </div>
            <div className="text-right">
              <p className="text-sm text-blue-100">Usuário logado:</p>
              <p className="text-lg font-semibold">{usuario}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-gray-300">
          {[
            { id: 'financeiro', label: 'Financeiro', icon: '💰' },
            { id: 'caixa', label: 'Caixa', icon: '📦' },
            { id: 'auditoria', label: 'Auditoria', icon: '📋' }
          ].map(({ id, label, icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`px-4 py-3 font-semibold flex items-center gap-2 border-b-2 transition ${
                tab === id
                  ? 'border-blue-600 text-blue-600 bg-white'
                  : 'border-transparent text-gray-600 bg-gray-100 hover:text-blue-500'
              }`}
            >
              {icon} {label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          {tab === 'financeiro' && <TabFinanceiro />}
          {tab === 'auditoria' && <TabAuditoria />}
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-gray-800 text-gray-300 mt-12 py-4 text-center text-sm">
        <p>webPosto API v0.2.0 • Desenvolvido para Grupo Lisboa • {new Date().getFullYear()}</p>
      </footer>
    </div>
  );
}
