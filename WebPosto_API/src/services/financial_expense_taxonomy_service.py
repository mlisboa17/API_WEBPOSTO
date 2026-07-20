"""Taxonomia gerencial explicável para despesas de postos e lojas."""

import re
import unicodedata
from typing import Any

from pydantic import BaseModel, ConfigDict


class ExpenseTaxonomySuggestion(BaseModel):
    model_config = ConfigDict(frozen=True)

    category: str
    subcategory: str
    accounting_nature: str
    suggested_department: str | None = None
    evidence: tuple[str, ...] = ()
    requires_review: bool = True


def _plain(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return re.sub(r"\s+", " ", "".join(c for c in normalized if not unicodedata.combining(c))).upper()


# Ordem específica antes das categorias compartilhadas.
RULES: tuple[tuple[str, str, str, str | None, tuple[str, ...]], ...] = (
    ("COMBUSTIVEIS - CMV", "LOGISTICA DO COMBUSTIVEL", "CMV", "combustiveis", ("FRETE COMBUST", "DESCARGA COMBUST", "SEGURO CARGA")),
    ("COMBUSTIVEIS - CMV", "COMPRAS DE COMBUSTIVEIS", "CMV", "combustiveis", ("GASOLINA", "ETANOL", "DIESEL S10", "DIESEL S500", "ARLA", "COMPRA COMBUST")),
    ("COMBUSTIVEIS - CMV", "AJUSTES DE ESTOQUE", "CMV", "combustiveis", ("EVAPORACAO", "PERDA COMBUST", "AJUSTE TANQUE")),
    ("LUBRIFICANTES - CMV", "MERCADORIAS PARA REVENDA", "CMV", "lubrificantes", ("LUBRIFIC", "OLEO MOTOR", "ADITIVO", "FILTRO", "PALHETA", "FLUIDO")),
    ("CONVENIENCIA - CMV", "MERCADORIAS PARA REVENDA", "CMV", "conveniencia", ("BEBIDA", "REFRIGERANTE", "ENERGETICO", "CERVEJA", "SALGADO", "CHOCOLATE", "SORVETE", "TABAC", "MERCADORIA REVENDA")),
    ("INSUMOS OPERACIONAIS", "LIMPEZA E CONSUMO", "OPEX", None, ("LIMPEZA", "SACOLA", "COPO DESCART", "EMBALAGEM", "GUARDANAPO", "PAPEL TOALHA", "PAPEL HIGIENICO", "MATERIAL DE COPA")),
    ("DESPESAS COM PESSOAL", "SALARIOS E REMUNERACAO", "OPEX", None, ("SALARIO", "PRO LABORE", "COMISSAO", "HORA EXTRA", "ADICIONAL NOTURNO", "GRATIFIC", "PREMIACAO")),
    ("DESPESAS COM PESSOAL", "ENCARGOS TRABALHISTAS", "OPEX", None, ("INSS", "FGTS", "FERIAS", "13 SALARIO", "RESCISAO", "TRABALHISTA")),
    ("ALIMENTACAO E BENEFICIOS", "BENEFICIOS", "OPEX", None, ("VALE ALIMENT", "VALE REFEI", "CESTA BASICA", "PLANO DE SAUDE", "VALE TRANSPORTE", "ALIMENTACAO FUNC")),
    ("ENERGIA, AGUA E UTILIDADES", "UTILIDADES", "OPEX", None, ("ENERGIA", "CELPE", "AGUA", "ESGOTO", "TELEFONE", "INTERNET", "GAS ")),
    ("IMPOSTOS E TAXAS", "TRIBUTOS E LICENCAS", "OPEX", None, ("PIS", "COFINS", "IRPJ", "CSLL", "ICMS", "ISS", "IPTU", "ALVARA", "LICENCA", "BOMBEIRO")),
    ("CONTABILIDADE E FISCAL", "SERVICOS CONTABEIS", "OPEX", None, ("CONTABIL", "ESCRITURACAO", "AUDITORIA", "CERTIFICADO DIGITAL")),
    ("JURIDICO", "SERVICOS JURIDICOS", "OPEX", None, ("ADVOG", "JURID", "JUDICIAL", "CARTORIO", "CONTRATO")),
    ("TECNOLOGIA E SISTEMAS", "SISTEMAS E EQUIPAMENTOS", "OPEX", None, ("SOFTWARE", "SISTEMA", "ERP", "COMPUTADOR", "IMPRESSORA", "BACKUP", "NUVEM")),
    ("MANUTENCAO E INFRAESTRUTURA", "MANUTENCAO", "OPEX", None, ("MANUTEN", "REPARO", "PINTURA", "ELETRICA", "HIDRAULICA", "JARDINAGEM")),
    ("LOGISTICA E TRANSPORTE", "FROTA E TRANSPORTE", "OPEX", None, ("PEDAGIO", "ESTACIONAMENTO", "RASTREAMENTO", "LOCACAO VEICULO", "FROTA")),
    ("SEGURANCA", "SEGURANCA PATRIMONIAL", "OPEX", None, ("VIGILANCIA", "MONITORAMENTO", "ALARME", "CAMERA", "EPI")),
    ("MARKETING E PUBLICIDADE", "DIVULGACAO E PROMOCOES", "OPEX", None, ("GOOGLE ADS", "META ADS", "OUTDOOR", "PANFLETO", "BANNER", "PROMOCAO", "FIDELIDADE", "PUBLICIDADE")),
    ("TAXAS BANCARIAS E CARTOES", "TARIFAS E ADQUIRENCIA", "OPEX", None, ("TARIFA BANC", "TAXA CARTAO", "ANTECIPACAO", "PROCESSAMENTO", "BOLETO", "TED")),
    ("DESPESAS FINANCEIRAS", "JUROS E ENCARGOS", "OPEX", None, ("JUROS", "EMPRESTIMO", "FINANCIAMENTO", "ENCARGO FINANCEIRO", "RENEGOCIACAO")),
    ("SEGUROS", "SEGUROS OPERACIONAIS", "OPEX", None, ("SEGURO EMPRES", "SEGURO PATRIM", "SEGURO FROTA", "SEGURO VIDA", "SEGURO AMBIENT")),
    ("INVESTIMENTOS", "CAPEX", "CAPEX", None, ("CONSTRUCAO", "REFORMA", "AMPLIACAO", "NOVA BOMBA", "NOVO TANQUE", "OBRA CIVIL", "AQUISICAO VEICULO")),
    ("DESPESAS ADMINISTRATIVAS", "MATERIAIS E SERVICOS", "OPEX", None, ("ESCRITORIO", "PAPELARIA", "IMPRESSAO", "CORREIO", "ASSINATURA", "CONSULTORIA", "TERCEIRIZADO")),
)


class FinancialExpenseTaxonomyService:
    FIELDS = ("planoConta", "planoContaGerencialDescricao", "descricao", "descricaoDocumento", "historico", "centroCusto", "fornecedor")

    def suggest(self, row: dict[str, Any]) -> ExpenseTaxonomySuggestion:
        text = _plain(" ".join(str(row.get(field) or "") for field in self.FIELDS))
        for category, subcategory, nature, department, markers in RULES:
            hits = tuple(marker for marker in markers if marker in text)
            if hits:
                return ExpenseTaxonomySuggestion(
                    category=category,
                    subcategory=subcategory,
                    accounting_nature=nature,
                    suggested_department=department,
                    evidence=hits,
                    requires_review=True,
                )
        return ExpenseTaxonomySuggestion(
            category="AGUARDANDO CLASSIFICACAO",
            subcategory="SEM EVIDENCIA SUFICIENTE",
            accounting_nature="NAO_DEFINIDA",
        )
