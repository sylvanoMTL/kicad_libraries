"""The footprint library is named on its own, apart from the symbol library (LIB-06, D-15).

Plan 10-11 separates the two names; the tests here are written so they also hold once plan 10-12 moves
footprints into the shared Atomic_Footprints library: they compare against the plan's footprint_link
and the footprint_library_for helper, never against the symbol library name directly.
"""

import dataclasses
from datetime import date

from customfixtures import BATTERY_CHARGER
from zipfixtures import footprint_library_for

from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.commit_plan import build_commit_plan, default_message
from kicad_lib_manager.importer.plan import InstallOptions, Resolution, ToolContext
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.importer.preview import preview_sections
from kicad_lib_manager.importer.verify import verify_install
from kicad_lib_manager.kicad_files import find_property, find_symbol, load
from kicad_lib_manager.models import Severity

LIBRARY = BATTERY_CHARGER
SYMBOL = "CSD85301Q2"
FOOTPRINT = "DQK0006B"


def test_footprint_link_runs_from_the_plan_to_every_consumer(atomic_custom, ul_package, tmp_path):
    _, candidate = ul_package
    options = InstallOptions(library=LIBRARY)
    plan = build_plan(candidate, options, atomic_custom, ToolContext())
    assert not plan.blocked, plan.issues
    link = f"{footprint_library_for(LIBRARY)}:{FOOTPRINT}"
    assert plan.footprint_library == footprint_library_for(LIBRARY)
    assert plan.footprint_link == link

    # The preview's Footprint row shows the link
    rewrites = next(s for s in preview_sections(plan, candidate, options) if s.name == "Path rewrites")
    row = next(r for r in rewrites.rows if r.text == "Footprint")
    assert row.detail.endswith(link)

    result = apply_plan(plan, backup_root=tmp_path / "bk")
    assert result.ok, result.issues
    assert not [i for i in verify_install(plan) if i.severity is Severity.ERROR]

    # The symbol on disk carries the same link
    library = load(atomic_custom.symbols_dir / f"{LIBRARY}.kicad_sym")
    symbol = find_symbol(library.root, SYMBOL)
    assert find_property(symbol.node, "Footprint").value == plan.footprint_link

    # The commit plan and its message name it too
    cplan = build_commit_plan(result, plan, vendor_label="Ultra Librarian", today=date(2026, 10, 27))
    assert cplan.footprint == plan.footprint_link
    assert f"Footprint: {plan.footprint_link}" in default_message(cplan)


def test_verify_expects_the_plans_footprint_link(atomic_custom, ul_package, tmp_path):
    _, candidate = ul_package
    plan = build_plan(candidate, InstallOptions(library=LIBRARY), atomic_custom, ToolContext())
    assert apply_plan(plan, backup_root=tmp_path / "bk").ok
    # A plan that expects another footprint library than the one written is caught
    wrong = dataclasses.replace(plan, footprint_library="Somewhere_Else")
    assert [i.code for i in verify_install(wrong) if i.severity is Severity.ERROR] == ["verify.link_unresolved"]


def test_a_kept_symbol_links_no_footprint(atomic_custom, ul_package, tmp_path):
    _, candidate = ul_package
    first = build_plan(candidate, InstallOptions(library=LIBRARY), atomic_custom, ToolContext())
    assert apply_plan(first, backup_root=tmp_path / "bk").ok
    # Make the installed symbol differ from the incoming one, so the same name is a real conflict
    sym_path = atomic_custom.symbols_dir / f"{LIBRARY}.kicad_sym"
    text = sym_path.read_text(encoding="utf-8")
    changed = text.replace('"Manufacturer" "TI"', '"Manufacturer" "Texas Instruments"')
    assert changed != text
    sym_path.write_text(changed, encoding="utf-8")

    key = f"symbol:{LIBRARY}:{SYMBOL}"
    options = InstallOptions(library=LIBRARY, resolutions={key: Resolution("skip")})
    plan = build_plan(candidate, options, atomic_custom, ToolContext())
    assert not plan.blocked, plan.issues
    assert plan.footprint_library is None
    assert plan.footprint_link is None
    assert plan.linked_footprint is None
