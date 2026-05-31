from __future__ import annotations

from src.domain.entities.cash_expense import ExpenseCategory

_KEYWORDS = {
    ExpenseCategory.FUEL: ("gasolina", "etanol", "diesel", "combustivel", "combustível"),
    ExpenseCategory.TAX: ("imposto", "tributo", "icms", "pis", "cofins", "taxa"),
    ExpenseCategory.PAYROLL: ("salario", "salário", "folha", "prolabore", "encargo"),
    ExpenseCategory.MAINTENANCE: ("manutencao", "manutenção", "reparo", "oficina", "peca", "peça"),
    ExpenseCategory.RENT: ("aluguel", "locacao", "locação", "arrendamento"),
    ExpenseCategory.UTILITIES: ("energia", "luz", "agua", "água", "internet", "telefone", "saneamento"),
    ExpenseCategory.SERVICE: ("servico", "serviço", "consultoria", "terceiro", "frete", "seguro"),
}


def map_description_to_category(description: str) -> ExpenseCategory:
    text = (description or "").strip().lower()
    if not text:
        return ExpenseCategory.OTHER

    for category, terms in _KEYWORDS.items():
        if any(term in text for term in terms):
            return category
    return ExpenseCategory.OTHER
