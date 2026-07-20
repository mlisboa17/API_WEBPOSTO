from src.core.management_scope import (
    LICENSED_COMPANY_CODES,
    MANAGEMENT_DEPARTMENTS,
    UNMAPPED_WEBPOSTO_GROUP_CODES,
    department_for_group,
    is_licensed_company,
)


def test_scope_contains_exactly_three_licensed_companies() -> None:
    assert LICENSED_COMPANY_CODES == frozenset({11495, 5555, 74014})


def test_scope_rejects_unlicensed_company() -> None:
    assert is_licensed_company(11495) is True
    assert is_licensed_company("74014") is True
    assert is_licensed_company(5333) is False


def test_departments_are_fixed_and_independent() -> None:
    assert MANAGEMENT_DEPARTMENTS == ("combustiveis", "conveniencia", "lubrificantes")


def test_real_webposto_groups_map_to_management_departments() -> None:
    assert department_for_group(24554) == "combustiveis"
    assert department_for_group("55444") == "conveniencia"
    assert department_for_group(24556) == "lubrificantes"


def test_ambiguous_groups_remain_unmapped() -> None:
    assert UNMAPPED_WEBPOSTO_GROUP_CODES == frozenset({25016, 26039, 29273})
    assert department_for_group(26039) is None
