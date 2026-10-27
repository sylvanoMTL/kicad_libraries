"""The footprint library is named on its own, apart from the symbol library (LIB-06, D-15).

Plan 10-11 separates the two names; the tests here are written so they also hold once plan 10-12 moves
footprints into the shared Atomic_Footprints library: they compare against the plan's footprint_link
and the footprint_library_for helper, never against the symbol library name directly.
"""

import dataclasses
from datetime import date

from customfixtures import ABSENT_LIBRARY, BATTERY_CHARGER
from zipfixtures import footprint_library_for

from kicad_lib_manager.importer import stems
from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.layout import RepoLayout
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


def test_footprint_library_for_is_the_shared_library():
    assert footprint_library_for(BATTERY_CHARGER) == stems.SHARED_FOOTPRINT_LIBRARY == "Atomic_Footprints"
    assert footprint_library_for(ABSENT_LIBRARY) == stems.SHARED_FOOTPRINT_LIBRARY


def test_tracer_new_symbol_library_comes_alone_with_a_shared_footprint(synthetic_custom, ul_package, tmp_path):
    _, candidate = ul_package
    # The v1 tree has no Atomic_Footprints.pretty yet
    assert not (synthetic_custom.footprints_dir / "Atomic_Footprints.pretty").exists()
    plan = build_plan(candidate, InstallOptions(library=ABSENT_LIBRARY), synthetic_custom, ToolContext())
    assert not plan.blocked, plan.issues

    shared = synthetic_custom.footprints_dir / "Atomic_Footprints.pretty"
    ops = {(op.kind, op.path) for op in plan.ops}
    assert ("mkdir", shared) in ops
    assert ("footprint", shared / "DQK0006B.kicad_mod") in ops
    assert ("symbol_lib", synthetic_custom.symbols_dir / f"{ABSENT_LIBRARY}.kicad_sym") in ops
    assert any(op.kind == "model" for op in plan.ops)
    assert not [op for op in plan.ops if op.path.name == f"{ABSENT_LIBRARY}.pretty"]
    assert "install.pair_completed" not in [i.code for i in plan.issues]
    assert plan.new_symbol_lib and plan.new_footprint_lib
    assert plan.new_library
    assert plan.pretty_path == shared
    assert plan.footprint_library == "Atomic_Footprints"
    assert plan.footprint_link == "Atomic_Footprints:DQK0006B"

    result = apply_plan(plan, backup_root=tmp_path / "bk")
    assert result.ok, result.issues
    assert not (synthetic_custom.footprints_dir / f"{ABSENT_LIBRARY}.pretty").exists()
    assert (shared / "DQK0006B.kicad_mod").is_file()
    assert not [i for i in verify_install(plan) if i.severity is Severity.ERROR]
    library = load(synthetic_custom.symbols_dir / f"{ABSENT_LIBRARY}.kicad_sym")
    symbol = find_symbol(library.root, SYMBOL)
    assert find_property(symbol.node, "Footprint").value == "Atomic_Footprints:DQK0006B"


def test_tracer_existing_library_writes_into_the_existing_shared_folder(atomic_custom, ul_package):
    _, candidate = ul_package
    shared = atomic_custom.footprints_dir / "Atomic_Footprints.pretty"
    assert shared.is_dir()
    plan = build_plan(candidate, InstallOptions(library=BATTERY_CHARGER), atomic_custom, ToolContext())
    assert not plan.blocked, plan.issues
    assert not [op for op in plan.ops if op.kind == "mkdir" and op.path.suffix == ".pretty"]
    assert ("footprint", shared / "DQK0006B.kicad_mod") in {(op.kind, op.path) for op in plan.ops}
    assert not plan.new_footprint_lib


def test_a_case_twin_of_the_shared_library_refuses(atomic_custom, ul_package):
    _, candidate = ul_package
    twin = atomic_custom.footprints_dir / "atomic_footprints.pretty"
    (atomic_custom.footprints_dir / "Atomic_Footprints.pretty").rename(atomic_custom.footprints_dir / "tmp_rename.pretty")
    (atomic_custom.footprints_dir / "tmp_rename.pretty").rename(twin)
    plan = build_plan(candidate, InstallOptions(library=LIBRARY), atomic_custom, ToolContext())
    assert plan.blocked and not plan.ops
    codes = [i.code for i in plan.issues if i.severity is Severity.ERROR]
    assert codes == ["install.library_case_clash"]
    text = next(i.text for i in plan.issues if i.code == "install.library_case_clash")
    assert text == (
        "Custom/Footprints holds atomic_footprints.pretty, which differs from Atomic_Footprints only by letter case; "
        "rename that folder to Atomic_Footprints"
    )


def test_a_missing_footprints_folder_names_the_shared_library(tmp_path, ul_package):
    _, candidate = ul_package
    layout = RepoLayout.for_repo(tmp_path)
    layout.symbols_dir.mkdir(parents=True)
    layout.models_dir.mkdir(parents=True)
    plan = build_plan(candidate, InstallOptions(library=ABSENT_LIBRARY), layout, ToolContext())
    assert plan.blocked and not plan.ops
    error = next(i for i in plan.issues if i.code == "install.footprints_dir_missing")
    assert error.text.startswith("Cannot create Atomic_Footprints: the Custom/Footprints folder is missing")


def test_an_existing_shared_library_gives_no_mkdir(atomic_custom, ul_package):
    _, candidate = ul_package
    plan = build_plan(candidate, InstallOptions(library=ABSENT_LIBRARY), atomic_custom, ToolContext())
    assert not plan.blocked, plan.issues
    assert not [op for op in plan.ops if op.kind == "mkdir" and op.path.suffix == ".pretty"]
    assert (plan.new_symbol_lib, plan.new_footprint_lib) == (True, False)


def test_a_second_new_library_reuses_the_folder_the_first_created(synthetic_custom, ul_package, tmp_path):
    _, candidate = ul_package
    first = build_plan(candidate, InstallOptions(library=ABSENT_LIBRARY), synthetic_custom, ToolContext())
    assert (first.new_symbol_lib, first.new_footprint_lib) == (True, True)
    assert apply_plan(first, backup_root=tmp_path / "bk").ok
    # Same footprint name again for another new library: the folder is shared, so the footprint is now identical
    second = build_plan(candidate, InstallOptions(library="Atomic_Transistor_BJT"), synthetic_custom, ToolContext())
    assert not [op for op in second.ops if op.kind == "mkdir" and op.path.suffix == ".pretty"]
    assert not second.blocked, second.issues
    assert (second.new_symbol_lib, second.new_footprint_lib) == (True, False)
    assert second.footprint_link == first.footprint_link


def test_an_existing_symbol_library_without_a_footprint_folder_installs_with_one_mkdir(synthetic_custom, ul_package, tmp_path):
    _, candidate = ul_package
    # The v1 tree keeps per-library folders and has no Atomic_Footprints.pretty; add a symbol-only Atomic_ library
    sym = synthetic_custom.symbols_dir
    source = next(sym.glob("*.kicad_sym"))
    (sym / f"{LIBRARY}.kicad_sym").write_bytes(source.read_bytes())
    plan = build_plan(candidate, InstallOptions(library=LIBRARY), synthetic_custom, ToolContext())
    assert not plan.blocked, plan.issues
    mkdirs = [op.path for op in plan.ops if op.kind == "mkdir" and op.path.suffix == ".pretty"]
    assert mkdirs == [synthetic_custom.footprints_dir / "Atomic_Footprints.pretty"]
    assert (plan.new_symbol_lib, plan.new_footprint_lib) == (False, True)
    assert not [i for i in plan.issues if i.severity is Severity.WARNING and "pair" in i.code]
