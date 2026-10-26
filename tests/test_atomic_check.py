"""Rule, fix-spec and finding unit tests for the atomic check (ATOM-01, FLD-02, D-10 to D-18)."""

import pytest

from customfixtures import (
    ATOMIC_EXPECTED,
    ATOMIC_FOOTPRINTS,
    ATOMIC_LIBRARIES,
    atomic_lib,
    atomic_part,
    write_atomic_custom,
    write_atomic_files,
    write_fake_kicad,
)
from kicad_lib_manager import kicad_files
from kicad_lib_manager.atomic_check import (
    ATOMIC_RULES,
    FILL_KINDS,
    SAFE_FIX_KINDS,
    AtomicContext,
    FootprintTarget,
    check_symbol,
    datasheet_problem,
    effective_mpn,
    repo_context,
)
from kicad_lib_manager.library_scanner import find_footprint_libs
from kicad_lib_manager.models import FixSpec, FootprintLibrary, SymbolEntry

REL = "Custom/Symbols/Atomic_T.kicad_sym"
NOT_A_LINK = "Datasheet is not a link or file path"


def _anywhere_ctx() -> AtomicContext:
    """A context in which every non-blank Library:Footprint resolves and every model is fine.

    The field rules below are not about footprints; the footprint and model tests use repo_context.
    """

    def resolve(text: str) -> FootprintTarget:
        if not text.strip():
            return FootprintTarget(text, "", "", None, None, "no footprint")
        library, _, footprint = text.partition(":")
        return FootprintTarget(text, library, footprint, None, None, None)

    return AtomicContext(resolve, lambda target: [])


def _check(
    lib_bytes: bytes, name: str, *, rel_path: str = REL, fixable: bool = True, ctx: AtomicContext | None = None
) -> SymbolEntry:
    loaded = kicad_files.parse_bytes(lib_bytes, "Atomic_T.kicad_sym")
    assert isinstance(loaded, kicad_files.LoadedFile), loaded
    return check_symbol(loaded.root, name, rel_path=rel_path, fixable=fixable, ctx=ctx or _anywhere_ctx())


def _entry(part, **kwargs) -> SymbolEntry:
    return _check(atomic_lib((part,)), part.name, **kwargs)


def _violation(entry: SymbolEntry, rule: str):
    found = [v for v in entry.violations if v.rule == rule]
    assert len(found) == 1, [v.rule for v in entry.violations]
    return found[0]


def _rules(entry: SymbolEntry) -> list[str]:
    return [v.rule for v in entry.violations]


# -- datasheet_problem ---------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    ["https://x.com/a.pdf", "HTTP://X.COM/A", "${KICAD_LIB_GITHUB}/docs/a.pdf", "C:/docs/a.pdf", "C:\\docs\\a.pdf", "/home/a.pdf"],
)
def test_datasheet_problem_accepts_a_link_a_variable_path_or_an_absolute_path(value):
    assert datasheet_problem(value) is None


@pytest.mark.parametrize("value", ["", "  ", "~"])
def test_datasheet_problem_calls_an_empty_value_no_datasheet(value):
    assert datasheet_problem(value) == "no datasheet"


@pytest.mark.parametrize("value", ["see website", "www.ti.com", "file:///C:/a.pdf", "docs/a.pdf"])
def test_datasheet_problem_rejects_text_that_is_not_a_link_or_a_path(value):
    assert datasheet_problem(value) == NOT_A_LINK


# -- MPN ------------------------------------------------------------------------


def test_mpn_missing_is_reported_without_a_fix():
    violation = _violation(_entry(atomic_part("P1", drop=("MPN",))), "mpn")

    assert violation.text == "no MPN"
    assert violation.fixes == ()
    assert violation.fill is None


@pytest.mark.parametrize("value", ["", "  ", "~", "None", "N/A", "n/a"])
def test_mpn_placeholder_values_count_as_absent(value):
    entry = _entry(atomic_part("P1", replace={"MPN": value}))

    assert _violation(entry, "mpn").text == "no MPN"


def test_mpn_stored_under_an_alias_name_gets_the_rename_fix():
    entry = _entry(atomic_part("P1", drop=("MPN",), extra=(("MP", "P1"),)))

    violation = _violation(entry, "mpn")
    assert violation.text == 'MPN is stored as "MP", not as "MPN"'
    assert violation.fixes == (FixSpec("rename_alias", REL, "P1", 'Rename "MP" to "MPN"', {"property": "MP", "new_name": "MPN"}),)


def test_mpn_in_several_fields_with_one_value_gets_one_merge_fix():
    entry = _entry(atomic_part("P1", extra=(("MP", "P1"),)))

    violation = _violation(entry, "mpn")
    assert violation.text == 'MPN is stored in several fields ("MPN", "MP")'
    assert len(violation.fixes) == 1
    fix = violation.fixes[0]
    assert fix.kind == "merge_alias"
    assert fix.params == {"group": "mpn", "keep": "MPN", "value": "P1"}
    assert fix.label == 'Merge "MPN" and "MP" into "MPN" = "P1"'


def test_mpn_fields_that_disagree_have_no_fix_only_choices():
    entry = _entry(atomic_part("P1", replace={"MPN": "A"}, extra=(("MP", "B"),)))

    violation = _violation(entry, "mpn")
    assert violation.text == 'MPN fields disagree ("A" in "MPN", "B" in "MP")'
    assert violation.fixes == ()
    assert violation.choices == ("A", "B")
    assert violation.fill == FixSpec("merge_alias", REL, "P1", "Keep one MPN value", {"group": "mpn", "keep": "MPN", "value": ""})


def test_mpn_blank_alias_next_to_a_good_mpn_is_ignored():
    entry = _entry(atomic_part("P1", extra=(("MP", ""),)))

    assert _rules(entry) == []


def test_effective_mpn_is_the_agreed_value_or_none():
    def mpn_of(part):
        loaded = kicad_files.parse_bytes(atomic_lib((part,)), "x.kicad_sym")
        return effective_mpn(kicad_files.find_symbol(loaded.root, part.name).node)

    assert mpn_of(atomic_part("P1")) == "P1"
    assert mpn_of(atomic_part("P1", drop=("MPN",), extra=(("MP", "P1"),))) == "P1"
    assert mpn_of(atomic_part("P1", drop=("MPN",))) is None
    assert mpn_of(atomic_part("P1", replace={"MPN": "A"}, extra=(("MP", "B"),))) is None


# -- Manufacturer -----------------------------------------------------------------


def test_manufacturer_missing_is_reported_without_a_fix():
    violation = _violation(_entry(atomic_part("P1", drop=("Manufacturer",))), "manufacturer")

    assert violation.text == "no manufacturer"
    assert violation.fixes == ()


@pytest.mark.parametrize("value", ["", " ", "~", "None", "N/A"])
def test_manufacturer_placeholder_values_count_as_absent(value):
    entry = _entry(atomic_part("P1", replace={"Manufacturer": value}))

    assert _violation(entry, "manufacturer").text == "no manufacturer"


def test_manufacturer_alias_spelling_is_reported_with_the_canonical_name_and_a_fix():
    violation = _violation(_entry(atomic_part("P1", replace={"Manufacturer": "TI"})), "manufacturer")

    assert violation.text == 'Manufacturer "TI" is not written as "Texas Instruments"'
    assert violation.fixes == (
        FixSpec(
            "canonical_manufacturer", REL, "P1", 'Manufacturer "TI" → "Texas Instruments"',
            {"property": "Manufacturer", "value": "Texas Instruments"},
        ),
    )


def test_manufacturer_canonical_spelling_passes():
    assert _rules(_entry(atomic_part("P1", replace={"Manufacturer": "Texas Instruments"}))) == []


def test_manufacturer_case_variant_of_the_canonical_name_is_a_spelling_problem():
    violation = _violation(_entry(atomic_part("P1", replace={"Manufacturer": "texas instruments"})), "manufacturer")

    assert violation.text == 'Manufacturer "texas instruments" is not written as "Texas Instruments"'


def test_manufacturer_stored_as_mf_with_an_alias_value_is_one_violation_with_two_fixes():
    entry = _entry(atomic_part("P1", drop=("Manufacturer",), extra=(("MF", "GCT"),)))

    violation = _violation(entry, "manufacturer")
    assert violation.text == (
        'Manufacturer is stored as "MF", not as "Manufacturer"; "GCT" is not written as "Global Connector Technology"'
    )
    assert [f.kind for f in violation.fixes] == ["rename_alias", "canonical_manufacturer"]
    assert all(f.params["property"] == "MF" for f in violation.fixes)
    assert violation.fixes[0].params == {"property": "MF", "new_name": "Manufacturer"}
    assert violation.fixes[1].params == {"property": "MF", "value": "Global Connector Technology"}


def test_manufacturer_several_fields_that_name_one_company_get_one_merge_fix():
    entry = _entry(
        atomic_part("P1", drop=("Manufacturer",), extra=(("MF", "GCT"), ("MANUFACTURER", "Global Connector Technology")))
    )

    violation = _violation(entry, "manufacturer")
    assert violation.text == 'Manufacturer is stored in several fields ("MF", "MANUFACTURER")'
    assert len(violation.fixes) == 1
    assert violation.fixes[0].kind == "merge_alias"
    assert violation.fixes[0].params == {"group": "manufacturer", "keep": "MF", "value": "Global Connector Technology"}


def test_manufacturer_several_fields_naming_different_companies_offer_choices():
    entry = _entry(atomic_part("P1", drop=("Manufacturer",), extra=(("MF", "GCT"), ("MANUFACTURER", "Molex"))))

    violation = _violation(entry, "manufacturer")
    assert violation.text == 'Manufacturer fields disagree ("GCT" in "MF", "Molex" in "MANUFACTURER")'
    assert violation.fixes == ()
    assert violation.choices == ("Global Connector Technology", "Molex")
    assert violation.fill.kind == "merge_alias"
    assert violation.fill.params == {"group": "manufacturer", "keep": "MF", "value": ""}


def test_manufacturer_not_in_the_table_passes_with_a_finding_and_no_fix():
    entry = _entry(atomic_part("P1", replace={"Manufacturer": "Hirose"}))

    assert entry.violations == []
    assert not entry.failing
    assert [(f.kind, f.text, f.fix) for f in entry.findings] == [
        ("unknown_manufacturer", 'manufacturer "Hirose" is not in the manufacturer table', None)
    ]


# -- Value --------------------------------------------------------------------------


def test_value_that_is_not_the_mpn_is_reported_with_a_fix():
    entry = _entry(atomic_part("P1", replace={"Value": "FFC20", "MPN": "FH12-20S-0.5SH"}))

    violation = _violation(entry, "value")
    assert violation.text == 'Value "FFC20" is not the MPN "FH12-20S-0.5SH"'
    assert violation.fixes == (
        FixSpec(
            "value_to_mpn", REL, "P1", 'Value "FFC20" → "FH12-20S-0.5SH"',
            {"property": "Value", "value": "FH12-20S-0.5SH"},
        ),
    )


@pytest.mark.parametrize("value", ["P1 ", " P1", "p1"])
def test_value_must_be_the_identical_string_to_the_mpn(value):
    entry = _entry(atomic_part("P1", replace={"Value": value}))

    assert _violation(entry, "value").text == f'Value "{value}" is not the MPN "P1"'


def test_value_equal_to_the_mpn_passes():
    assert _rules(_entry(atomic_part("P1"))) == []


def test_value_is_not_reported_when_no_mpn_can_be_determined():
    assert _rules(_entry(atomic_part("P1", replace={"Value": "other"}, drop=("MPN",)))) == ["mpn"]
    entry = _entry(atomic_part("P1", replace={"Value": "other", "MPN": "A"}, extra=(("MP", "B"),)))
    assert _rules(entry) == ["mpn"]


# -- leftovers ----------------------------------------------------------------------


def test_price_and_stock_leftovers_are_findings_with_a_remove_fix_and_never_fail_the_symbol():
    entry = _entry(
        atomic_part("P1", extra=(("Price", "1.20"), ("Availability", "In stock"), ("Check_prices", "x")))
    )

    assert not entry.failing
    assert [f.kind for f in entry.findings] == ["leftover"] * 3
    first = entry.findings[0]
    assert first.text == 'leftover price/stock data "Price"'
    assert first.fix == FixSpec("remove_leftover", REL, "P1", 'Remove "Price"', {"property": "Price"})


def test_a_ki_field_or_a_standard_field_is_never_a_leftover():
    entry = _entry(atomic_part("P1", extra=(("ki_keywords", "a b"), ("ki_description", "d"), ("Sim.Device", "R"))))

    assert entry.findings == []


# -- not fixable ----------------------------------------------------------------------


def test_nothing_outside_custom_carries_a_fix_a_fill_or_choices():
    parts = (
        atomic_part("A", drop=("MPN",), extra=(("MP", "A"),)),
        atomic_part("B", replace={"MPN": "X"}, extra=(("MP", "Y"),)),
        atomic_part("C", replace={"Manufacturer": "TI", "Datasheet": "", "Description": ""}),
        atomic_part("D", replace={"Value": "other"}, extra=(("Price", "1"),)),
    )
    for part in parts:
        entry = _entry(part, fixable=False)
        assert entry.violations
        for violation in entry.violations:
            assert violation.fixes == () and violation.fill is None and violation.choices == ()
        for finding in entry.findings:
            assert finding.fix is None


# -- ordering, kinds and the shared inventory --------------------------------------------


def test_violations_follow_the_fixed_rule_order():
    part = atomic_part(
        "P1", replace={"Value": "other", "Datasheet": "", "Description": ""}, drop=("Manufacturer",),
        extra=(("MP", "P1"),),
    )
    entry = _entry(part)

    # MPN is stored twice (MPN and MP), no manufacturer, Value fails, then datasheet and description
    assert _rules(entry) == ["mpn", "manufacturer", "value", "datasheet", "description"]
    assert _rules(entry) == sorted(_rules(entry), key=ATOMIC_RULES.index)


def test_every_offered_fix_and_fill_kind_is_a_known_kind():
    library = next(lib for lib in ATOMIC_LIBRARIES if lib.name == "Atomic_Connector")
    data = atomic_lib(library.symbols)
    for symbol in library.symbols:
        entry = _check(data, symbol.name)
        for violation in entry.violations:
            assert all(fix.kind in SAFE_FIX_KINDS for fix in violation.fixes)
            if violation.fill is not None:
                assert violation.fill.kind in FILL_KINDS or (violation.fill.kind == "merge_alias" and violation.choices)
        for finding in entry.findings:
            assert finding.fix is None or finding.fix.kind in SAFE_FIX_KINDS


def _inventory_ctx(tmp_path) -> AtomicContext:
    """A context over the whole written inventory and the fake KiCad install."""
    root = tmp_path / "repo"
    write_atomic_custom(root)
    return repo_context(root, find_footprint_libs(root), write_fake_kicad(tmp_path)[0])


def test_the_inventory_symbols_produce_exactly_their_expected_rule_sets(tmp_path):
    library = next(lib for lib in ATOMIC_LIBRARIES if lib.name == "Atomic_Connector")
    data = atomic_lib(library.symbols)
    ctx = _inventory_ctx(tmp_path)
    for symbol in library.symbols:
        entry = _check(data, symbol.name, ctx=ctx)
        assert frozenset(_rules(entry)) == ATOMIC_EXPECTED[("Atomic_Connector", symbol.name)], symbol.name


def test_a_symbol_with_two_broken_rules_still_fails_once():
    entry = _entry(atomic_part("P1", drop=("MPN", "Manufacturer")))

    assert entry.failing
    assert _rules(entry) == ["mpn", "manufacturer"]


# -- derived symbols (ATOM-02, D-22) ----------------------------------------------------------


def _family(parent, *children, child_first: bool = False) -> bytes:
    parts = (*children, parent) if child_first else (parent, *children)
    return atomic_lib(parts)


def test_derived_child_takes_a_missing_manufacturer_from_its_parent():
    parent = atomic_part("PARENT")
    child = atomic_part("CHILD", drop=("Manufacturer",), extends="PARENT")

    entry = _check(_family(parent, child), "CHILD")

    assert entry.extends == "PARENT"
    assert entry.violations == []


def test_derived_child_without_its_own_mpn_fails_even_when_the_parent_has_one():
    parent = atomic_part("PARENT")
    child = atomic_part("CHILD", drop=("MPN",), extends="PARENT")

    data = _family(parent, child)

    assert _violation(_check(data, "CHILD"), "mpn").text == "no MPN of its own (the parent's MPN does not count)"
    assert _rules(_check(data, "PARENT")) == []
    assert _violation(_entry(atomic_part("BASE", drop=("MPN",))), "mpn").text == "no MPN"


def test_derived_child_with_the_same_mpn_as_its_parent_still_needs_its_own_property():
    parent = atomic_part("PARENT", replace={"MPN": "SHARED", "Value": "SHARED"})
    child = atomic_part("CHILD", replace={"MPN": "SHARED", "Value": "SHARED"}, extends="PARENT")

    assert _check(_family(parent, child), "CHILD").violations == []


def test_derived_child_keeps_its_own_blank_datasheet_and_description():
    parent = atomic_part("PARENT")
    child = atomic_part("CHILD", replace={"Datasheet": "~", "Description": ""}, extends="PARENT")

    entry = _check(_family(parent, child), "CHILD")

    assert _violation(entry, "datasheet").text == "no datasheet"
    assert _violation(entry, "description").text == "no description"


def test_derived_children_report_an_inherited_manufacturer_and_fix_it_in_the_parent():
    parent = atomic_part("PARENT", replace={"Manufacturer": "TI"})
    kids = (
        atomic_part("KID-A", drop=("Manufacturer",), extends="PARENT"),
        atomic_part("KID-B", drop=("Manufacturer",), extends="PARENT"),
    )
    data = _family(parent, *kids)

    for kid in kids:
        violation = _violation(_check(data, kid.name), "manufacturer")
        assert violation.text == 'Manufacturer "TI" is not written as "Texas Instruments" (inherited from "PARENT")'
        assert len(violation.fixes) == 1
        fix = violation.fixes[0]
        assert fix.kind == "canonical_manufacturer" and fix.symbol == "PARENT"
        assert fix.label.endswith(' (in parent "PARENT"; its other variants change too)')
        assert fix.params == {"property": "Manufacturer", "value": "Texas Instruments"}


def test_derived_child_inherits_a_missing_datasheet_and_its_fill_points_at_the_parent():
    parent = atomic_part("PARENT", replace={"Datasheet": ""})
    child = atomic_part("CHILD", drop=("Datasheet",), extends="PARENT")

    violation = _violation(_check(_family(parent, child), "CHILD"), "datasheet")

    assert violation.text == 'no datasheet (inherited from "PARENT")'
    assert violation.fill.symbol == "PARENT"
    assert violation.fill.label == 'Fill in the datasheet link (in parent "PARENT"; its other variants change too)'


def test_derived_child_of_a_missing_parent_is_still_checked_and_says_so():
    child = atomic_part("CHILD", drop=("Manufacturer", "Datasheet", "Description"), extends="NOT-THERE")

    entry = _check(atomic_lib((child,)), "CHILD")

    assert _violation(entry, "manufacturer").text == 'no manufacturer (its parent symbol "NOT-THERE" is missing)'
    assert _violation(entry, "datasheet").text == 'no datasheet (its parent symbol "NOT-THERE" is missing)'
    assert _violation(entry, "description").text == 'no description (its parent symbol "NOT-THERE" is missing)'
    own = _check(atomic_lib((atomic_part("CHILD", replace={"Value": "x"}, extends="NOT-THERE"),)), "CHILD")
    assert _violation(own, "value").text == 'Value "x" is not the MPN "CHILD"'


def test_derived_child_written_before_its_parent_gets_the_same_results():
    parent = atomic_part("PARENT", replace={"Manufacturer": "TI", "Description": ""})
    child = atomic_part("CHILD", drop=("Manufacturer", "Description"), extends="PARENT")

    after = _check(_family(parent, child), "CHILD")
    before = _check(_family(parent, child, child_first=True), "CHILD")

    assert after.violations == before.violations
    assert _rules(after) == ["manufacturer", "description"]


def test_derived_pair_from_the_vendor_builder_gives_the_same_results_in_either_order():
    from installfixtures import extends_pair

    first = _check(extends_pair(child_first=False), "CHILD_Y")
    second = _check(extends_pair(child_first=True), "CHILD_Y")

    assert first.violations == second.violations
    # the vendor child declares an empty Footprint of its own, so that rule fails too
    assert _rules(first) == ["mpn", "manufacturer", "footprint", "datasheet", "description"]


def test_derived_grandchild_takes_an_absent_property_from_the_nearest_declaring_ancestor():
    root = atomic_part("ROOT", replace={"Manufacturer": "TI"})
    middle = atomic_part("MIDDLE", drop=("Manufacturer",), extends="ROOT")
    leaf = atomic_part("LEAF", drop=("Manufacturer",), extends="MIDDLE")

    violation = _violation(_check(atomic_lib((root, middle, leaf)), "LEAF"), "manufacturer")

    assert violation.text.endswith('(inherited from "ROOT")')
    assert violation.fixes[0].symbol == "ROOT"


def test_a_symbol_that_extends_itself_does_not_loop():
    loop = atomic_part("LOOP", drop=("Manufacturer",), extends="LOOP")

    entry = _check(atomic_lib((loop,)), "LOOP")

    assert _rules(entry) == ["manufacturer"]


# -- footprint rule (D-20) ------------------------------------------------------

FP_LIB = FootprintLibrary(ATOMIC_FOOTPRINTS, f"Custom/Footprints/{ATOMIC_FOOTPRINTS}.pretty", "Custom")


def _repo(tmp_path, *, kicad: bool = True):
    """Write the Atomic_Footprints library and optionally the fake KiCad install; return (repo root, KiCad footprints dir)."""
    root = tmp_path / "repo"
    write_atomic_files(root / "Custom")
    kicad_dir = write_fake_kicad(tmp_path)[0] if kicad else None
    return root, kicad_dir


def _fp_ctx(tmp_path, *, kicad: bool = True, libs: tuple[FootprintLibrary, ...] = (FP_LIB,)) -> AtomicContext:
    root, kicad_dir = _repo(tmp_path, kicad=kicad)
    return repo_context(root, list(libs), kicad_dir)


def _fp_entry(tmp_path, text: str, **kwargs) -> SymbolEntry:
    part = atomic_part("P1", replace={"Footprint": text})
    return _check(atomic_lib((part,)), "P1", ctx=_fp_ctx(tmp_path, **kwargs))


def test_footprint_in_a_repo_library_resolves_to_its_file_and_repo_path(tmp_path):
    target = _fp_ctx(tmp_path).resolve_footprint(f"{ATOMIC_FOOTPRINTS}:GENERIC-2PIN")

    assert target.problem is None
    assert (target.library, target.footprint) == (ATOMIC_FOOTPRINTS, "GENERIC-2PIN")
    assert target.rel_path == f"Custom/Footprints/{ATOMIC_FOOTPRINTS}.pretty/GENERIC-2PIN.kicad_mod"
    assert target.path is not None and target.path.is_file()


def test_footprint_in_a_kicad_library_resolves_with_no_repo_path(tmp_path):
    target = _fp_ctx(tmp_path).resolve_footprint("Package_TO_SOT_SMD:SOT-23-5")

    assert target.problem is None
    assert target.rel_path is None
    assert target.path is not None and target.path.name == "SOT-23-5.kicad_mod"


@pytest.mark.parametrize("text", ["", "   ", "~"])
def test_footprint_blank_field_says_no_footprint(tmp_path, text):
    violation = _violation(_fp_entry(tmp_path, text), "footprint")

    assert violation.text == "no footprint"
    assert violation.fixes == ()
    assert violation.fill is None


@pytest.mark.parametrize("text", ["GENERIC-2PIN", ":GENERIC-2PIN", f"{ATOMIC_FOOTPRINTS}:"])
def test_footprint_without_a_library_or_a_name_says_what_is_expected(tmp_path, text):
    violation = _violation(_fp_entry(tmp_path, text), "footprint")

    assert violation.text == f'Footprint "{text}" does not name a library (expected Library:Footprint)'


def test_footprint_library_that_does_not_exist_is_not_found(tmp_path):
    violation = _violation(_fp_entry(tmp_path, "Nope_Library:GENERIC-2PIN"), "footprint")

    assert violation.text == 'footprint library "Nope_Library" was not found'


def test_footprint_library_name_is_case_sensitive_for_the_library_too(tmp_path):
    violation = _violation(_fp_entry(tmp_path, "atomic_footprints:GENERIC-2PIN"), "footprint")

    assert violation.text == 'footprint library "atomic_footprints" was not found'


def test_footprint_missing_from_its_library_is_named(tmp_path):
    violation = _violation(_fp_entry(tmp_path, f"{ATOMIC_FOOTPRINTS}:NOT-THERE"), "footprint")

    assert violation.text == f'footprint "NOT-THERE" is not in library "{ATOMIC_FOOTPRINTS}"'


def test_footprint_wrong_case_fails_even_on_a_case_insensitive_disk(tmp_path):
    violation = _violation(_fp_entry(tmp_path, f"{ATOMIC_FOOTPRINTS}:generic-2pin"), "footprint")

    assert violation.text == f'footprint "generic-2pin" is not in library "{ATOMIC_FOOTPRINTS}"'


def test_footprint_library_defined_twice_in_the_repo_is_ambiguous(tmp_path):
    twin = FootprintLibrary(ATOMIC_FOOTPRINTS, f"Other/Footprints/{ATOMIC_FOOTPRINTS}.pretty", "Other")

    entry = _fp_entry(tmp_path, f"{ATOMIC_FOOTPRINTS}:GENERIC-2PIN", libs=(FP_LIB, twin))

    assert _violation(entry, "footprint").text == f'footprint library "{ATOMIC_FOOTPRINTS}" is defined more than once'


def test_footprint_library_sharing_a_nickname_with_a_kicad_library_is_ambiguous(tmp_path):
    clash = FootprintLibrary("Package_TO_SOT_SMD", "Custom/Footprints/Package_TO_SOT_SMD.pretty", "Custom")

    entry = _fp_entry(tmp_path, "Package_TO_SOT_SMD:SOT-23-5", libs=(FP_LIB, clash))

    assert _violation(entry, "footprint").text == 'footprint library "Package_TO_SOT_SMD" is defined more than once'


@pytest.mark.parametrize("kicad_dir", ["none", "missing"])
def test_footprint_kicad_library_is_not_found_when_the_kicad_folder_is_unknown(tmp_path, kicad_dir):
    root, _ = _repo(tmp_path, kicad=False)
    given = None if kicad_dir == "none" else tmp_path / "no_kicad"

    target = repo_context(root, [FP_LIB], given).resolve_footprint("Package_TO_SOT_SMD:SOT-23-5")

    assert target.problem == 'footprint library "Package_TO_SOT_SMD" was not found'


@pytest.mark.parametrize(
    "text",
    [
        f"{ATOMIC_FOOTPRINTS}:../{ATOMIC_FOOTPRINTS}.pretty/GENERIC-2PIN",
        f"{ATOMIC_FOOTPRINTS}:..\\x",
        "..:x",
        f"{ATOMIC_FOOTPRINTS}:.",
    ],
)
def test_footprint_text_with_dots_and_separators_never_resolves_to_a_path(tmp_path, text):
    target = _fp_ctx(tmp_path).resolve_footprint(text)

    assert target.problem is not None
    assert target.path is None


def test_footprint_a_derived_symbol_without_its_own_takes_it_from_the_parent_and_says_so(tmp_path):
    parent = atomic_part("PARENT", replace={"Footprint": f"{ATOMIC_FOOTPRINTS}:NOT-THERE"})
    child = atomic_part("CHILD", drop=("Footprint",), extends="PARENT")

    entry = _check(atomic_lib((parent, child)), "CHILD", ctx=_fp_ctx(tmp_path))

    assert _violation(entry, "footprint").text == (
        f'footprint "NOT-THERE" is not in library "{ATOMIC_FOOTPRINTS}" (inherited from "PARENT")'
    )


def test_footprint_rule_comes_between_manufacturer_and_value_in_the_reporting_order(tmp_path):
    part = atomic_part("P1", drop=("Manufacturer",), replace={"Footprint": "", "Value": "x"})

    entry = _check(atomic_lib((part,)), "P1", ctx=_fp_ctx(tmp_path))

    assert _rules(entry) == ["manufacturer", "footprint", "value"]
