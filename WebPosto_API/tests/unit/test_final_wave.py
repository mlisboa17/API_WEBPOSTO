from src.operational.product_registration.final_wave import (
    LEGITIMATE_VARIANT,
    SAME_PRODUCT,
    UNRESOLVED_DUPLICATE,
    classify_final_duplicate,
    majority_treatment,
    pick_icms_row,
    score_icms_row,
)


class _Row:
    def __init__(self, referencia, cst_entrada="000", icms_entrada=18.0, csosn="0", fcp=0.0):
        self.referencia = referencia
        self.cst_entrada = cst_entrada
        self.icms_entrada = icms_entrada
        self.csosn_entrada = csosn
        self.csosn_saida = csosn
        self.fcp = fcp


def test_same_product_is_already_registered():
    label, _ = classify_final_duplicate(
        "CERVEJA IMPERIO PURO MALTE LATA 350 ML", "CERVEJA IMPERIO PURO MALTE 350 ML"
    )
    assert label == SAME_PRODUCT


def test_measure_difference_is_legitimate_variant():
    label, _ = classify_final_duplicate("CERVEJA IMPERIO GOLD 330ML", "CERVEJA IMPERIO GOLD 269ML")
    assert label == LEGITIMATE_VARIANT


def test_missing_measure_is_unresolved():
    label, _ = classify_final_duplicate("SALG PINGO OURO PICANHA 55G NOVO", "PINGO DE OURO PICANHA")
    assert label == UNRESOLVED_DUPLICATE


def test_usb_c_versus_micro_usb_is_legitimate_variant():
    label, _ = classify_final_duplicate(
        "CABO I2GO USB C PARA USB C 1,2M", "CABO I2GO MICRO USB ANDROID USB USB A 1,2M"
    )
    assert label == LEGITIMATE_VARIANT


def test_icms_score_prefers_verified_reference():
    verified = _Row("0000000099")
    other = _Row("0000000001")
    score_v, _ = score_icms_row(
        verified, verified_references={"0000000099"}, expected_cst_entrada="000", expected_rate=18.0
    )
    score_o, _ = score_icms_row(
        other, verified_references={"0000000099"}, expected_cst_entrada="000", expected_rate=18.0
    )
    assert score_v > score_o


def test_extra_flavor_on_candidate_is_legitimate_variant():
    label, _ = classify_final_duplicate(
        "CERVEJA IMPERIO GOLD LATA 350 ML", "CERVEJA IMPERIO LATA 350 ML"
    )
    assert label == LEGITIMATE_VARIANT


def test_icms_tie_uses_lowest_reference():
    first = _Row("0000000008")
    second = _Row("0000000003")
    chosen, reason = pick_icms_row(
        [first, second], verified_references=set(), expected_cst_entrada="000", expected_rate=18.0
    )
    assert chosen.referencia == "0000000003"
    assert reason == "OWNER_ACCEPTED_DETERMINISTIC_TIEBREAK"


def test_majority_treatment_uses_distinct_invoices():
    winner, rate, discarded = majority_treatment(
        [
            {"nfe": "1/1", "classification": "ST_COMPROVADA"},
            {"nfe": "2/1", "classification": "ST_COMPROVADA"},
            {"nfe": "3/1", "classification": "SEM_ST_COMPROVADA", "aliquotaEntrada": 18},
        ]
    )
    assert winner == "ST_COMPROVADA"
    assert rate is None
    assert discarded == [{"classification": "SEM_ST_COMPROVADA", "notas": 1}]
