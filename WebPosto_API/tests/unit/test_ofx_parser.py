"""Testes do parser OFX (D02+ conciliação cartão x banco).

Usa uma fixture OFX sintética (dados anonimizados) que replica a estrutura real observada nos
extratos PagBank/PagSeguro (Posto Doze e Casa Caiada): cabeçalho SGML + STMTTRN com as 3
categorias de MEMO conhecidas (venda de cartão, PIX recebido, pagamento de conta).
"""
from __future__ import annotations

from src.domain.reconciliation.bank_statement import BankTransactionCategory
from src.domain.reconciliation.ofx_parser import parse_ofx

_SAMPLE_OFX = """OFXHEADER:100
DATA:OFXSGML
VERSION:100
SECURITY:NONE
ENCODING:UTF-8
CHARSET:NONE
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX><SIGNONMSGSRSV1><SONRS><STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS><DTSERVER>20260710120000[-3:BRT]</DTSERVER><LANGUAGE>POR</LANGUAGE><FI><ORG>PagSeguro Internet S/A</ORG><FID>290</FID></FI></SONRS></SIGNONMSGSRSV1><BANKMSGSRSV1><STMTTRNRS><STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS><STMTRS><CURDEF>BRL</CURDEF><BANKACCTFROM><BANKID>290</BANKID><ACCTID>00000000-0</ACCTID><ACCTTYPE>CHECKING</ACCTTYPE></BANKACCTFROM><BANKTRANLIST><DTSTART>20260701000000[-3:BRT]</DTSTART><DTEND>20260710000000[-3:BRT]</DTEND>
<STMTTRN><TRNTYPE>IN</TRNTYPE><DTPOSTED>20260701093000[-3:BRT]</DTPOSTED><TRNAMT>150.75</TRNAMT><FITID>aaaa1111-1111-1111-1111-111111111111</FITID><MEMO>Vendas - Disponivel DEBITO VISA</MEMO></STMTTRN>
<STMTTRN><TRNTYPE>IN</TRNTYPE><DTPOSTED>20260701101500[-3:BRT]</DTPOSTED><TRNAMT>48.30</TRNAMT><FITID>aaaa2222-2222-2222-2222-222222222222</FITID><MEMO>Vendas - Disponivel CREDITO MASTERCARD</MEMO></STMTTRN>
<STMTTRN><TRNTYPE>OUT</TRNTYPE><DTPOSTED>20260702080000[-3:BRT]</DTPOSTED><TRNAMT>-1000.00</TRNAMT><FITID>bbbb1111-1111-1111-1111-111111111111</FITID><MEMO>Pagamento de conta - Fornecedor Exemplo Ltda</MEMO></STMTTRN>
<STMTTRN><TRNTYPE>IN</TRNTYPE><DTPOSTED>20260703140000[-3:BRT]</DTPOSTED><TRNAMT>502.06</TRNAMT><FITID>cccc1111-1111-1111-1111-111111111111</FITID><MEMO>Pix recebido - Vibra Energia S.a</MEMO></STMTTRN>
<STMTTRN><TRNTYPE>IN</TRNTYPE><DTPOSTED>20260703150000[-3:BRT]</DTPOSTED><TRNAMT>2000.00</TRNAMT><FITID>dddd1111-1111-1111-1111-111111111111</FITID><MEMO>Pix recebido - Auto Posto Exemplo Ltda</MEMO></STMTTRN>
</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>
"""


def test_parse_ofx_header_metadata():
    statement = parse_ofx(_SAMPLE_OFX)

    assert statement.org == "PagSeguro Internet S/A"
    assert statement.fid == "290"
    assert statement.bankId == "290"
    assert statement.acctId == "00000000-0"
    assert statement.acctType == "CHECKING"
    assert statement.periodStart.isoformat() == "2026-07-01T00:00:00"
    assert statement.periodEnd.isoformat() == "2026-07-10T00:00:00"
    assert len(statement.transactions) == 5


def test_parse_ofx_classifies_card_settlement():
    statement = parse_ofx(_SAMPLE_OFX)
    card_txns = [t for t in statement.transactions if t.category == BankTransactionCategory.CARD_SETTLEMENT]

    assert len(card_txns) == 2
    debit_visa = next(t for t in card_txns if t.cardBrand == "VISA")
    assert debit_visa.cardMethod == "DEBITO"
    assert debit_visa.amount == 150.75
    assert debit_visa.trnType == "IN"

    credit_master = next(t for t in card_txns if t.cardBrand == "MASTERCARD")
    assert credit_master.cardMethod == "CREDITO"
    assert credit_master.amount == 48.30


def test_parse_ofx_classifies_bill_payment():
    statement = parse_ofx(_SAMPLE_OFX)
    bills = [t for t in statement.transactions if t.category == BankTransactionCategory.BILL_PAYMENT]

    assert len(bills) == 1
    assert bills[0].counterparty == "Fornecedor Exemplo Ltda"
    assert bills[0].amount == -1000.00


def test_parse_ofx_flags_premmia_pix_from_vibra():
    statement = parse_ofx(_SAMPLE_OFX)
    pix_txns = [t for t in statement.transactions if t.category == BankTransactionCategory.PIX_RECEIVED]

    assert len(pix_txns) == 2
    vibra_pix = next(t for t in pix_txns if "Vibra" in t.counterparty)
    assert vibra_pix.likelyPremmia is True
    assert vibra_pix.amount == 502.06

    other_pix = next(t for t in pix_txns if "Vibra" not in t.counterparty)
    assert other_pix.likelyPremmia is False


# --- Itaú + adquirente (Rede/Cielo), formato observado no Posto Vip ---
# Tags de folha SEM fechamento (SGML puro) e liquidação agregada por dia+bandeira+método.
_SAMPLE_OFX_ITAU = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<SIGNONMSGSRSV1>
<SONRS>
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
<DTSERVER>20260710100000[-03:EST]
<LANGUAGE>POR
</SONRS>
</SIGNONMSGSRSV1>
<BANKMSGSRSV1>
<STMTTRNRS>
<TRNUID>1001
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
<STMTRS>
<CURDEF>BRL
<BANKACCTFROM>
<BANKID>0341
<ACCTID>0000000000
<ACCTTYPE>CHECKING
</BANKACCTFROM>
<BANKTRANLIST>
<DTSTART>20260701100000[-03:EST]
<DTEND>20260710100000[-03:EST]
<STMTTRN>
<TRNTYPE>CREDIT
<DTPOSTED>20260710100000[-03:EST]
<TRNAMT>0.00
<FITID>20260710001
<CHECKNUM>20260710001
<MEMO>SALDO TOTAL DISPONÍVEL DIA
</STMTTRN>
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20260710100000[-03:EST]
<TRNAMT>-14498.15
<FITID>20260710002
<CHECKNUM>20260710002
<MEMO>TRANSFERÊNCIA AUTOM. ENVIADA 3175.19802-1
</STMTTRN>
<STMTTRN>
<TRNTYPE>CREDIT
<DTPOSTED>20260710100000[-03:EST]
<TRNAMT>2546.88
<FITID>20260710003
<CHECKNUM>20260710003
<MEMO>RECEBIMENTO REDE VISA AT0011148381 REDECARD INSTITUICAO DE PAGAMENTO S.A. 01.425.787/0001-04
</STMTTRN>
<STMTTRN>
<TRNTYPE>CREDIT
<DTPOSTED>20260710100000[-03:EST]
<TRNAMT>485.12
<FITID>20260710004
<CHECKNUM>20260710004
<MEMO>RECEBIMENTO CIELO MAST DB1003946779 CIELO S.A - INSTITUICAO DE PAGAMENTO 01.027.058/0001-91
</STMTTRN>
<STMTTRN>
<TRNTYPE>CREDIT
<DTPOSTED>20260709100000[-03:EST]
<TRNAMT>0.00
<FITID>20260709001
<CHECKNUM>20260709001
<MEMO>SALDO ANTERIOR
</STMTTRN>
</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>
"""


def test_parse_ofx_itau_classifies_acquirer_card_settlement():
    statement = parse_ofx(_SAMPLE_OFX_ITAU)
    card_txns = [t for t in statement.transactions if t.category == BankTransactionCategory.CARD_SETTLEMENT]

    assert len(card_txns) == 2
    rede_visa = next(t for t in card_txns if t.acquirer == "REDE")
    assert rede_visa.cardBrand == "VISA"
    assert rede_visa.cardMethod == "CREDITO"
    assert rede_visa.settlementCode == "AT"
    assert rede_visa.trnType == "CREDIT"

    cielo_mast = next(t for t in card_txns if t.acquirer == "CIELO")
    assert cielo_mast.cardBrand == "MASTERCARD"
    assert cielo_mast.cardMethod == "DEBITO"
    assert cielo_mast.settlementCode == "DB"


def test_parse_ofx_itau_classifies_automatic_transfer_and_balance_info():
    statement = parse_ofx(_SAMPLE_OFX_ITAU)

    transfer = next(t for t in statement.transactions if t.category == BankTransactionCategory.AUTOMATIC_TRANSFER)
    assert transfer.amount == -14498.15
    assert transfer.counterparty == "3175.19802-1"

    balances = [t for t in statement.transactions if t.category == BankTransactionCategory.BALANCE_INFO]
    assert len(balances) == 2
    assert all(t.amount == 0.0 for t in balances if "TOTAL" in t.memo.upper())
