"""Vocabulário financeiro oficial do webposto CODEX.

Mantém separados fatos de resultado, obrigações e movimentos de tesouraria.
Os rótulos deste módulo são os que devem chegar às telas da Diretoria.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict


class FinancialConcept(str, Enum):
    FINANCIAL_EXPENSE = "DESPESA_FINANCEIRA"
    ACCOUNT_PAYABLE = "CONTA_A_PAGAR"
    CASH_REGISTER_EXPENSE = "DESPESA_DE_CAIXA"
    CASH_WITHDRAWAL = "SANGRIA"
    CASH_SUPPLY = "SUPRIMENTO_DE_CAIXA"
    ACCOUNT_MOVEMENT = "MOVIMENTO_DE_CONTA"
    CASH_CLOSING = "FECHAMENTO_DE_CAIXA"


class Impact(str, Enum):
    YES = "SIM"
    NO = "NAO"
    DEPENDS_ON_RECONCILIATION = "DEPENDE_DA_CONCILIACAO"


class FinancialVocabularyEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    concept: FinancialConcept
    director_label: str
    webposto_source: str
    webposto_fields: tuple[str, ...]
    meaning: str
    affects_dre: Impact
    affects_cash: Impact
    direct_evidence: bool = True
    warning: str | None = None


FINANCIAL_VOCABULARY: dict[FinancialConcept, FinancialVocabularyEntry] = {
    FinancialConcept.FINANCIAL_EXPENSE: FinancialVocabularyEntry(
        concept=FinancialConcept.FINANCIAL_EXPENSE,
        director_label="Despesas financeiras e operacionais",
        webposto_source="CONSULTAR_DESPESAS_FINANCEIRO_REDE",
        webposto_fields=(
            "empresaCodigo",
            "planoContaGerencialCodigo",
            "descricaoDocumento",
            "data",
            "valor",
        ),
        meaning="Lançamento de despesa classificado no plano de contas gerencial.",
        affects_dre=Impact.YES,
        affects_cash=Impact.DEPENDS_ON_RECONCILIATION,
        warning="Não informa vencimento, pagamento, caixa, fornecedor ou sangria.",
    ),
    FinancialConcept.ACCOUNT_PAYABLE: FinancialVocabularyEntry(
        concept=FinancialConcept.ACCOUNT_PAYABLE,
        director_label="Contas a pagar",
        webposto_source="TITULO_PAGAR",
        webposto_fields=("valor", "valorPago", "vencimento", "dataPagamento", "situacao"),
        meaning="Obrigação com fornecedor, aberta ou paga, controlada por vencimento.",
        affects_dre=Impact.DEPENDS_ON_RECONCILIATION,
        affects_cash=Impact.DEPENDS_ON_RECONCILIATION,
        warning="Título em aberto não é saída de caixa; título pago não deve duplicar a despesa.",
    ),
    FinancialConcept.CASH_REGISTER_EXPENSE: FinancialVocabularyEntry(
        concept=FinancialConcept.CASH_REGISTER_EXPENSE,
        director_label="Despesas pagas no caixa",
        webposto_source="CAIXA_APRESENTADO",
        webposto_fields=("despesaApurado", "despesaApresentado", "despesaDiferenca"),
        meaning="Despesa registrada e conferida no fechamento do turno/caixa.",
        affects_dre=Impact.DEPENDS_ON_RECONCILIATION,
        affects_cash=Impact.YES,
        warning="Conciliar com despesas financeiras antes de somar à DRE.",
    ),
    FinancialConcept.CASH_WITHDRAWAL: FinancialVocabularyEntry(
        concept=FinancialConcept.CASH_WITHDRAWAL,
        director_label="Sangrias (retiradas de numerário)",
        webposto_source="SEM_CAMPO_DIRETO_CONFIRMADO",
        webposto_fields=(),
        meaning="Retirada física de dinheiro do caixa para cofre ou tesouraria.",
        affects_dre=Impact.NO,
        affects_cash=Impact.NO,
        direct_evidence=False,
        warning="Altera a localização do dinheiro, não o caixa consolidado nem o resultado.",
    ),
    FinancialConcept.CASH_SUPPLY: FinancialVocabularyEntry(
        concept=FinancialConcept.CASH_SUPPLY,
        director_label="Suprimentos de caixa",
        webposto_source="CAIXA_APRESENTADO",
        webposto_fields=("suprimentoCaixa",),
        meaning="Entrada de numerário para reforçar o caixa.",
        affects_dre=Impact.NO,
        affects_cash=Impact.NO,
        warning="Transferência interna; não é receita.",
    ),
    FinancialConcept.ACCOUNT_MOVEMENT: FinancialVocabularyEntry(
        concept=FinancialConcept.ACCOUNT_MOVEMENT,
        director_label="Movimentações de contas e tesouraria",
        webposto_source="MOVIMENTO_CONTA",
        webposto_fields=("tipo", "valor", "contaCodigo", "tipoDocumentoOrigem", "conciliado"),
        meaning="Débito ou crédito em conta financeira.",
        affects_dre=Impact.DEPENDS_ON_RECONCILIATION,
        affects_cash=Impact.YES,
        warning="Débito não significa automaticamente despesa; crédito não significa receita.",
    ),
    FinancialConcept.CASH_CLOSING: FinancialVocabularyEntry(
        concept=FinancialConcept.CASH_CLOSING,
        director_label="Fechamentos de caixa",
        webposto_source="CAIXA + CAIXA_APRESENTADO",
        webposto_fields=("apurado", "consolidado", "diferenca", "fechado"),
        meaning="Conferência do movimento do turno e dos valores informados pelo operador.",
        affects_dre=Impact.NO,
        affects_cash=Impact.DEPENDS_ON_RECONCILIATION,
        warning="Diferença de caixa é indicador de auditoria, não despesa operacional automática.",
    ),
}


def financial_vocabulary_entry(concept: FinancialConcept) -> FinancialVocabularyEntry:
    return FINANCIAL_VOCABULARY[concept]
