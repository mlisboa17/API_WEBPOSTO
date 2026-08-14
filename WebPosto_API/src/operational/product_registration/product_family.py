"""Classificacao de familia fiscal por descricao de produto.

Fonte unica usada pelo gerador de bases candidatas e pela matriz tributaria, para que
os dois nao divirjam. A familia e apenas um agrupamento para buscar evidencia; ela
nao define tributacao por si.
"""

from __future__ import annotations

import re
import unicodedata

BISCOITOS = "BISCOITOS"
AMENDOINS = "AMENDOINS"
SALGADINHOS_INDUSTRIALIZADOS = "SALGADINHOS_INDUSTRIALIZADOS"
CHIPS_BANANA = "CHIPS_BANANA"
CHIPS_BATATA_DOCE = "CHIPS_BATATA_DOCE"
CHIPS_MACAXEIRA = "CHIPS_MACAXEIRA"
CHIPS_OUTROS = "CHIPS_OUTROS"


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]+", " ", value.upper()).strip()


def family(description: str) -> str:
    """Agrupa a descricao numa familia fiscal candidata.

    A ordem importa: batata-doce e macaxeira precisam ser testadas antes de batata
    frita industrializada, senao caem em salgadinhos.
    """
    text = normalize(description)

    if "BANANA" in text:
        return CHIPS_BANANA
    if "BATATA DOCE" in text:
        return CHIPS_BATATA_DOCE
    if "MACAXEIRA" in text or "AIPIM" in text or "MANDIOCA" in text:
        return CHIPS_MACAXEIRA
    if "AMENDOIM" in text or "MENDORATO" in text:
        return AMENDOINS
    if "BISCOITO" in text or "TRAKINAS" in text or "COOKIE" in text or "WAFER" in text:
        return BISCOITOS
    if any(
        word in text
        for word in (
            "RUFFLES",
            "CEBOLITOS",
            "SALGADINHO",
            "PIPPOS",
            "CROCANTISSIMO",
            "DORITOS",
            "FANDANGOS",
            "CHEETOS",
            "BATATA",
        )
    ):
        return SALGADINHOS_INDUSTRIALIZADOS
    return CHIPS_OUTROS


# Famílias comerciais amplas, usadas para decidir se uma evidência de terceiro fala do
# mesmo tipo de mercadoria. A ordem importa: termos mais específicos vêm antes, senão
# "bolacha recheada" cairia em biscoito antes de ser reconhecida como recheada, e
# "água de coco" cairia em água mineral.
COMMERCIAL_FAMILIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("PIPOCA", ("PIPOCA", "POPCORN")),
    ("AMENDOIM", ("AMENDOIM", "MENDORATO", "CASTANHA", "NOZES", "PISTACHE")),
    ("BISCOITO", ("BISCOITO", "BISC ", "BISC.", "BOLACHA", "COOKIE", "WAFER", "WAFFER",
                  "TRAKINAS", "PASSATEMPO", "NEGRESCO", "OREO", "TORTINI", "TREVINHO")),
    ("BOLO_INDUSTRIAL", ("BOLINHO", "BOLO", "ROCAMBOLE", "PANETONE", "MINI CAKE")),
    ("SALGADINHO", ("SALGADINHO", "SALG ", "STIKSY", "PINGO", "RUFFLES", "CEBOLITOS",
                    "DORITOS", "FANDANGOS", "CHEETOS", "TORCIDA", "AMANTEIGADO CHIPS")),
    ("CHOCOLATE", ("CHOCOLATE", "BOMBOM", "TRUFA", "KITKAT", "KIT KAT", "BATON",
                   "PRESTIGIO", "DIAMANTE NEGRO", "TALENTO", "OURO BRANCO", "SONHO DE VALSA")),
    ("BALA_GOMA", ("BALA", "CHICLE", "CHICLETE", "PIRULITO", "GOMA", "JUJUBA", "MARSHMALLOW",
                   "HALLS", "TRIDENT", "MENTOS", "FINI")),
    ("BARRA_CEREAL", ("BARRA DE CEREAL", "BARRA CEREAL", "GRANOLA", "CEREAL MATINAL")),
    ("SORVETE", ("SORVETE", "PICOLE", "ACAI")),
    ("CONGELADO_PRONTO", ("COXINHA", "PASTEL", "PIZZA", "LASANHA", "EMPADA", "ESFIHA",
                          "KIBE", "NUGGETS", "HAMBURGUER", "SALGADO ASSADO", "PAO DE QUEIJO")),
    ("LACTEO", ("LEITE", "IOGURTE", "QUEIJO", "REQUEIJAO", "MANTEIGA", "MARGARINA",
                "CREME DE LEITE", "LEITE CONDENSADO")),
    ("REFRIGERANTE", ("REFRIGERANTE", "COCA COLA", "COCA-COLA", "GUARANA", "PEPSI",
                      "FANTA", "SPRITE", "SODA", "TONICA", "SCHWEPPES")),
    ("SUCO", ("SUCO", "NECTAR", "REFRESCO", "AGUA DE COCO")),
    ("ENERGETICO", ("ENERGETICO", "RED BULL", "MONSTER", "BALY", "FUSION")),
    ("AGUA", ("AGUA MINERAL", "AGUA SEM GAS", "AGUA COM GAS", "AGUA NATURAL")),
    ("CERVEJA", ("CERVEJA", "CHOPP", "IPA", "LAGER", "PILSEN")),
    ("VINHO_ESPUMANTE", ("VINHO", "ESPUMANTE", "PROSECCO", "SANGRIA")),
    ("DESTILADO", ("WHISKY", "WHISKEY", "VODKA", "CACHACA", "GIN", "RUM", "TEQUILA",
                   "CONHAQUE", "LICOR", "APERITIVO")),
    ("CAFE_CHA", ("CAFE", "CAPPUCCINO", "CHA ", "MATE")),
    ("MERCEARIA", ("ACUCAR", "ARROZ", "FEIJAO", "MACARRAO", "FARINHA", "OLEO DE SOJA",
                   "AZEITE", "SAL ", "VINAGRE", "KETCHUP", "MAIONESE", "MOSTARDA",
                   "MOLHO", "TEMPERO")),
    ("TABACARIA", ("CIGARRO", "TABACO", "FUMO", "SEDA", "ISQUEIRO", "NARGUILE")),
    ("HIGIENE", ("ABSORVENTE", "DESODORANTE", "SABONETE", "SHAMPOO", "CONDICIONADOR",
                 "PAPEL HIGIENICO", "FRALDA", "CREME DENTAL", "ESCOVA DENTAL",
                 "PRESERVATIVO", "LENCO", "ALCOOL EM GEL", "HIDRATANTE", "LAMINA")),
    ("LIMPEZA", ("DETERGENTE", "SABAO", "AGUA SANITARIA", "DESINFETANTE", "AMACIANTE",
                 "ESPONJA", "SACO DE LIXO", "PANO DE")),
    ("UTILIDADE", ("PILHA", "CARREGADOR", "CABO USB", "FONE", "GELO", "CARVAO",
                   "COPO", "GUARDANAPO", "FOSFORO")),
    ("FARMACIA", ("DIPIRONA", "PARACETAMOL", "IBUPROFENO", "ANTIACIDO", "SORO",
                  "ANALGESICO", "COMPRIMIDO")),
)


def commercial_family(description: str) -> str | None:
    """Família comercial ampla da descrição, ou None quando não reconhecida.

    Diferente de `family`, não tem categoria de sobra: descrição que não casa devolve
    None, porque afirmar família igual sem reconhecer o produto seria inventar evidência.
    O termo casa como palavra inteira, para que "SAL" não seja encontrado em
    "SALGADINHO" nem "CHA" em "CHAMPAGNE".
    """
    text = normalize(description)
    for name, keywords in COMMERCIAL_FAMILIES:
        for keyword in keywords:
            term = normalize(keyword)
            if term and re.search(rf"(?<![A-Z0-9]){re.escape(term)}(?![A-Z0-9])", text):
                return name
    return None
