"""Testes F04.0 — Operator Sales Intelligence."""
from __future__ import annotations

from src.services.employee_dimension_service import EmployeeDimensionService
from src.services.operator_sales_intelligence_service import (
    OperatorSalesIntelligenceService,
    _payment_bucket,
    _productivity_band,
)


def test_payment_bucket_pix():
    assert _payment_bucket("PIX MAQUININHA") == "PIX"


def test_productivity_band_elite():
    assert _productivity_band(92) == "ELITE"


def test_employee_dimension_mapping():
    rows = [
        {
            "funcionarioCodigo": 123,
            "nome": "TESTE OPERADOR",
            "cpf": "000.000.000-00",
            "funcionarioReferencia": "00001",
            "ativo": True,
            "empresaCodigo": 5555,
        }
    ]
    dim = EmployeeDimensionService.to_dimension(rows)
    assert len(dim) == 1
    assert dim[0]["employeeName"] == "TESTE OPERADOR"
    assert dim[0]["employeeStatus"] == "ATIVO"


def test_sales_performance_aggregation():
    svc = OperatorSalesIntelligenceService()
    idx = {10: {"employeeName": "Op Ten"}}
    venda = [
        {"funcionarioCodigo": 10, "totalVenda": 100, "cancelada": False},
        {"funcionarioCodigo": 10, "totalVenda": 50, "cancelada": False},
    ]
    venda_item = [
        {"funcionarioCodigo": 10, "totalVenda": 80, "bicoCodigo": 1, "quantidade": 20},
        {"funcionarioCodigo": 10, "totalVenda": 20, "quantidade": 2},
    ]
    sales = svc._sales_performance(venda, venda_item, idx)
    assert len(sales) == 1
    assert sales[0]["totalVendas"] == 150.0
    assert sales[0]["quantidadeVendas"] == 2
    assert sales[0]["volumeCombustivel"] == 80.0
    assert sales[0]["volumeConveniencia"] == 20.0
