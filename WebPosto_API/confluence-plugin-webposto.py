"""
Plugin Confluence — Integração webPosto API
Sincroniza Financeiro e Caixa do webPosto em Confluence
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, List, Any


class WebPostoConfluencePlugin:
    """Plugin que integra webPosto API com Confluence"""

    def __init__(self, api_url: str = "http://localhost:5000"):
        self.api_url = api_url
        self.api_endpoint_financeiro = f"{api_url}/sync/financeiro"
        self.api_endpoint_caixa = f"{api_url}/sync/caixa"
        self.api_endpoint_health = f"{api_url}/health"

    async def check_health(self) -> bool:
        """Verifica se API está online"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.api_endpoint_health, timeout=5) as resp:
                    return resp.status == 200
        except Exception as e:
            print(f"❌ Erro ao verificar health: {e}")
            return False

    async def fetch_financeiro(self) -> Dict[str, Any]:
        """Busca dados de Financeiro (Títulos)"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.api_endpoint_financeiro, timeout=10
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        return {"error": f"HTTP {resp.status}"}
        except Exception as e:
            return {"error": str(e)}

    async def fetch_caixa(self) -> Dict[str, Any]:
        """Busca dados de Caixa"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.api_endpoint_caixa, timeout=10) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        return {"error": f"HTTP {resp.status}"}
        except Exception as e:
            return {"error": str(e)}

    async def get_all_data(self) -> Dict[str, Any]:
        """Busca todos os dados (financeiro + caixa)"""
        financeiro = await self.fetch_financeiro()
        caixa = await self.fetch_caixa()

        return {
            "timestamp": datetime.now().isoformat(),
            "financeiro": financeiro,
            "caixa": caixa,
        }

    def format_confluence_table(self, data: Dict[str, Any]) -> str:
        """Formata dados para tabela Confluence"""
        html = """
        <table>
            <tr>
                <th>Tipo</th>
                <th>Descrição</th>
                <th>Valor (R$)</th>
                <th>Status</th>
            </tr>
        """

        # Financeiro
        if "financeiro" in data and "detalhes" in data["financeiro"]:
            for item in data["financeiro"]["detalhes"]:
                status = "✅ Pago" if item.get("pago") else "⏳ Pendente"
                html += f"""
                <tr>
                    <td>{item.get('tipo', 'N/A')}</td>
                    <td>{item.get('descricao', 'N/A')}</td>
                    <td>R$ {item.get('valor', 0):.2f}</td>
                    <td>{status}</td>
                </tr>
                """

        html += "</table>"
        return html

    def format_confluence_macro(self, data: Dict[str, Any]) -> str:
        """Formata como macro Confluence"""
        financeiro = data.get("financeiro", {})
        caixa = data.get("caixa", {})

        return f"""
<ac:structured-macro ac:name="info">
    <ac:parameter ac:name="title">webPosto Sync — Financeiro e Caixa</ac:parameter>
    <ac:rich-text-body>
        <p>
            <strong>Financeiro:</strong> {financeiro.get('registros', 0)} registros<br/>
            <strong>Caixa:</strong> {caixa.get('registros', 0)} registros<br/>
            <strong>Atualizado:</strong> {data.get('timestamp', 'N/A')}
        </p>
    </ac:rich-text-body>
</ac:structured-macro>
        """

    async def create_confluence_page_content(self, data: Dict[str, Any]) -> str:
        """Cria conteúdo completo para página Confluence"""
        timestamp = data.get("timestamp", "N/A")
        financeiro = data.get("financeiro", {})
        caixa = data.get("caixa", {})

        content = f"""
<h1>🏢 webPosto — Financeiro e Caixa</h1>

<p><em>Última sincronização: {timestamp}</em></p>

<h2>💰 Financeiro</h2>
<p><strong>Total de títulos:</strong> {financeiro.get('registros', 0)}</p>

<h3>Títulos a Receber/Pagar</h3>
{self._format_financeiro_table(financeiro.get('detalhes', []))}

<h2>🏦 Movimento de Caixa</h2>
<p><strong>Total de movimentos:</strong> {caixa.get('registros', 0)}</p>

<h3>Saldos de Caixa</h3>
{self._format_caixa_table(caixa.get('detalhes', []))}

<hr/>

<p>
    <strong>Status da API:</strong>
    <span ac:macro="status" ac:parameter="colour">Green</span>
    <em>webPosto API funcionando corretamente</em>
</p>
        """
        return content

    @staticmethod
    def _format_financeiro_table(items: List[Dict]) -> str:
        """Formata tabela de financeiro"""
        if not items:
            return "<p>Nenhum registro encontrado.</p>"

        html = "<table><tr><th>Tipo</th><th>Descrição</th><th>Valor</th><th>Vencimento</th><th>Status</th></tr>"

        for item in items:
            status = "✅ Pago" if item.get("pago") else "⏳ Pendente"
            tipo = item.get("tipo", "N/A")
            desc = item.get("descricao", "N/A")
            valor = f"R$ {item.get('valor', 0):.2f}"
            venc = item.get("data_vencimento", "N/A")

            html += f"<tr><td>{tipo}</td><td>{desc}</td><td>{valor}</td><td>{venc}</td><td>{status}</td></tr>"

        html += "</table>"
        return html

    @staticmethod
    def _format_caixa_table(items: List[Dict]) -> str:
        """Formata tabela de caixa"""
        if not items:
            return "<p>Nenhum registro encontrado.</p>"

        html = "<table><tr><th>Descrição</th><th>Saldo (R$)</th><th>Data</th></tr>"

        for item in items:
            desc = item.get("descricao", "N/A")
            saldo = f"R$ {item.get('saldo', 0):.2f}"
            data = item.get("data_movimento", "N/A")

            html += f"<tr><td>{desc}</td><td>{saldo}</td><td>{data}</td></tr>"

        html += "</table>"
        return html


# ========== EXEMPLO DE USO ==========


async def example_usage():
    """Exemplo de como usar o plugin"""
    plugin = WebPostoConfluencePlugin(api_url="http://localhost:5000")

    # Verificar saúde
    health = await plugin.check_health()
    print(f"API Status: {'✅ Online' if health else '❌ Offline'}")

    # Buscar dados
    print("\n📊 Buscando dados...")
    data = await plugin.get_all_data()

    # Formatar para Confluence
    print("\n📝 Conteúdo para Confluence:")
    confluence_content = await plugin.create_confluence_page_content(data)
    print(confluence_content)

    # Salvar como JSON para integração
    with open("webposto_confluence_data.json", "w") as f:
        json.dump(data, f, indent=2)
    print("\n✅ Dados salvos em webposto_confluence_data.json")


if __name__ == "__main__":
    # Rodar exemplo
    asyncio.run(example_usage())
