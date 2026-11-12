"""The footprint library is named on its own, apart from the symbol library (LIB-06, D-15).

Plan 10-11 separates the two names; the tests here are written so they also hold once plan 10-12 moves
footprints into the shared Atomic_Footprints library: they compare against the plan's footprint_link
and the footprint_library_for helper, never against the symbol library name directly.
"""

import dataclasses
import re
from datetime import date

from customfixtures import ABSENT_LIBRARY, BATTERY_CHARGER, atomic_lib, atomic_part
from installfixtures import UL_DESCRIPTION
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
    options = InstallOptions(library=LIBRARY, description=UL_DESCRIPTION)
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
    plan = build_plan(candidate, InstallOptions(library=LIBRARY, description=UL_DESCRIPTION), atomic_custom, ToolContext())
    assert apply_plan(plan, backup_root=tmp_path / "bk").ok
    # A plan that expects another footprint library than the one written is caught
    wrong = dataclasses.replace(plan, footprint_library="Somewhere_Else")
    assert [i.code for i in verify_install(wrong) if i.severity is Severity.ERROR] == ["verify.link_unresolved"]


def test_a_kept_symbol_links_no_footprint(atomic_custom, ul_package, tmp_path):
    _, candidate = ul_package
    first = build_plan(candidate, InstallOptions(library=LIBRARY, description=UL_DESCRIPTION), atomic_custom, ToolContext())
    assert apply_plan(first, backup_root=tmp_path / "bk").ok
    # Make the installed symbol differ from the incoming one, so the same name is a real conflict
    sym_path = atomic_custom.symbols_dir / f"{LIBRARY}.kicad_sym"
    text = sym_path.read_text(encoding="utf-8")
    changed = text.replace('"Manufacturer" "Texas Instruments"', '"Manufacturer" "Other Maker"')
    assert changed != text
    sym_path.write_text(changed, encoding="utf-8")

    key = f"symbol:{LIBRARY}:{SYMBOL}"
    options = InstallOptions(library=LIBRARY, description=UL_DESCRIPTION, resolutions={key: Resolution("skip")})
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
    plan = build_plan(candidate, InstallOptions(library=ABSENT_LIBRARY, description=UL_DESCRIPTION), synthetic_custom, ToolContext())
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
    plan = build_plan(candidate, InstallOptions(library=BATTERY_CHARGER, description=UL_DESCRIPTION), atomic_custom, ToolContext())
    assert not plan.blocked, plan.issues
    assert not [op for op in plan.ops if op.kind == "mkdir" and op.path.suffix == ".pretty"]
    assert ("footprint", shared / "DQK0006B.kicad_mod") in {(op.kind, op.path) for op in plan.ops}
    assert not plan.new_footprint_lib


def test_a_case_twin_of_the_shared_library_refuses(atomic_custom, ul_package):
    _, candidate = ul_package
    twin = atomic_custom.footprints_dir / "atomic_footprints.pretty"
    (atomic_custom.footprints_dir / "Atomic_Footprints.pretty").rename(atomic_custom.footprints_dir / "tmp_rename.pretty")
    (atomic_custom.footprints_dir / "tmp_rename.pretty").rename(twin)
    plan = build_plan(candidate, InstallOptions(library=LIBRARY, description=UL_DESCRIPTION), atomic_custom, ToolContext())
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
    plan = build_plan(candidate, InstallOptions(library=ABSENT_LIBRARY, description=UL_DESCRIPTION), layout, ToolContext())
    assert plan.blocked and not plan.ops
    error = next(i for i in plan.issues if i.code == "install.footprints_dir_missing")
    assert error.text.startswith("Cannot create Atomic_Footprints: the Custom/Footprints folder is missing")


def test_an_existing_shared_library_gives_no_mkdir(atomic_custom, ul_package):
    _, candidate = ul_package
    plan = build_plan(candidate, InstallOptions(library=ABSENT_LIBRARY, description=UL_DESCRIPTION), atomic_custom, ToolContext())
    assert not plan.blocked, plan.issues
    assert not [op for op in plan.ops if op.kind == "mkdir" and op.path.suffix == ".pretty"]
    assert (plan.new_symbol_lib, plan.new_footprint_lib) == (True, False)


def test_a_second_new_library_reuses_the_folder_the_first_created(synthetic_custom, ul_package, tmp_path):
    _, candidate = ul_package
    first = build_plan(candidate, InstallOptions(library=ABSENT_LIBRARY, description=UL_DESCRIPTION), synthetic_custom, ToolContext())
    assert (first.new_symbol_lib, first.new_footprint_lib) == (True, True)
    assert apply_plan(first, backup_root=tmp_path / "bk").ok
    # Same footprint name again for another new library: the folder is shared, so the footprint is now identical
    second = build_plan(candidate, InstallOptions(library="Atomic_Transistor_BJT", description=UL_DESCRIPTION), synthetic_custom, ToolContext())
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
    plan = build_plan(candidate, InstallOptions(library=LIBRARY, description=UL_DESCRIPTION), synthetic_custom, ToolContext())
    assert not plan.blocked, plan.issues
    mkdirs = [op.path for op in plan.ops if op.kind == "mkdir" and op.path.suffix == ".pretty"]
    assert mkdirs == [synthetic_custom.footprints_dir / "Atomic_Footprints.pretty"]
    assert (plan.new_symbol_lib, plan.new_footprint_lib) == (False, True)
    assert not [i for i in plan.issues if i.severity is Severity.WARNING and "pair" in i.code]


# D-19: the clash rules of the shared footprint library

SHARED = "Atomic_Footprints"


def _install_first(atomic_custom, candidate, tmp_path, library=ABSENT_LIBRARY):
    plan = build_plan(candidate, InstallOptions(library=library, description=UL_DESCRIPTION), atomic_custom, ToolContext())
    assert not plan.blocked, plan.issues
    assert apply_plan(plan, backup_root=tmp_path / "bk").ok
    return atomic_custom.footprints_dir / f"{SHARED}.pretty" / f"{FOOTPRINT}.kicad_mod"


def _reformat(path):
    """The same footprint with LF line endings and a tab for each two-space indent."""
    text = path.read_bytes().decode("utf-8")
    lines = text.replace("\r\n", "\n").split("\n")
    changed = "\n".join(re.sub(r"^((?:  )+)", lambda m: "\t" * (len(m.group(1)) // 2), line) for line in lines)
    assert changed != text
    path.write_bytes(changed.encode("utf-8"))


def _change_a_pad(path):
    text = path.read_text(encoding="utf-8")
    changed = text.replace("(size ", "(size 9 ", 1)
    assert changed != text
    path.write_bytes(changed.encode("utf-8"))


def test_tracer_the_same_footprint_in_another_format_is_reused(atomic_custom, ul_package, tmp_path):
    _, candidate = ul_package
    installed = _install_first(atomic_custom, candidate, tmp_path)
    _reformat(installed)

    plan = build_plan(candidate, InstallOptions(library=ABSENT_LIBRARY, description=UL_DESCRIPTION), atomic_custom, ToolContext())
    assert not plan.blocked, plan.issues
    assert not [op for op in plan.ops if op.kind == "footprint"]
    assert not [c for c in plan.conflicts if c.kind == "footprint"]
    reused = [i for i in plan.issues if i.code == "install.footprint_reused"]
    assert [i.severity for i in reused] == [Severity.INFO]
    assert reused[0].text == f"{FOOTPRINT} already in {SHARED} is the same footprint; it is reused and not written"
    assert plan.footprint_link == f"{SHARED}:{FOOTPRINT}"


def test_tracer_a_different_footprint_offers_the_part_number_as_its_new_name(atomic_custom, ul_package, tmp_path):
    _, candidate = ul_package
    installed = _install_first(atomic_custom, candidate, tmp_path)
    _change_a_pad(installed)

    plan = build_plan(candidate, InstallOptions(library=ABSENT_LIBRARY, description=UL_DESCRIPTION), atomic_custom, ToolContext())
    conflicts = [c for c in plan.conflicts if c.kind == "footprint"]
    assert len(conflicts) == 1
    assert conflicts[0].suggested_name == f"{FOOTPRINT}_{SYMBOL}"
    assert not [i for i in plan.issues if i.code == "install.footprint_reused"]


# D-19: Overwrite names the other parts that link the footprint

LINK = f"{SHARED}:{FOOTPRINT}"
FP_KEY = f"footprint:{SHARED}:{FOOTPRINT.casefold()}"


def _library_linking(layout, library, parts):
    """Write Custom/Symbols/<library>.kicad_sym holding parts, each (name, footprint link)."""
    symbols = tuple(atomic_part(name, replace={"Footprint": link}) for name, link in parts)
    (layout.symbols_dir / f"{library}.kicad_sym").write_bytes(atomic_lib(symbols))


def _clash(atomic_custom, candidate, tmp_path):
    """Install the part, then change the installed footprint so a second install clashes."""
    installed = _install_first(atomic_custom, candidate, tmp_path)
    _change_a_pad(installed)
    return installed


def test_the_conflict_names_every_other_part_linking_the_footprint(atomic_custom, ul_package, tmp_path):
    _, candidate = ul_package
    _clash(atomic_custom, candidate, tmp_path)
    _library_linking(atomic_custom, BATTERY_CHARGER, [("PARTA", LINK), ("PARTB", LINK)])

    plan = build_plan(candidate, InstallOptions(library=ABSENT_LIBRARY, description=UL_DESCRIPTION), atomic_custom, ToolContext())
    conflict = next(c for c in plan.conflicts if c.kind == "footprint")
    assert conflict.existing.endswith(
        "; it is linked by 2 other parts: PARTA (Atomic_Battery_Management), PARTB (Atomic_Battery_Management)"
    )


def test_one_linking_part_reads_as_part_not_parts(atomic_custom, ul_package, tmp_path):
    _, candidate = ul_package
    _clash(atomic_custom, candidate, tmp_path)
    _library_linking(atomic_custom, BATTERY_CHARGER, [("PARTA", LINK)])

    plan = build_plan(candidate, InstallOptions(library=ABSENT_LIBRARY, description=UL_DESCRIPTION), atomic_custom, ToolContext())
    conflict = next(c for c in plan.conflicts if c.kind == "footprint")
    assert conflict.existing.endswith("; it is linked by 1 other part: PARTA (Atomic_Battery_Management)")


def test_overwrite_warns_with_the_parts_it_changes(atomic_custom, ul_package, tmp_path):
    _, candidate = ul_package
    _clash(atomic_custom, candidate, tmp_path)
    _library_linking(atomic_custom, BATTERY_CHARGER, [("PARTA", LINK), ("PARTB", LINK)])

    options = InstallOptions(library=ABSENT_LIBRARY, description=UL_DESCRIPTION, resolutions={FP_KEY: Resolution("overwrite")})
    plan = build_plan(candidate, options, atomic_custom, ToolContext())
    assert not plan.blocked, plan.issues
    shared = [i for i in plan.issues if i.code == "install.footprint_shared"]
    assert [i.severity for i in shared] == [Severity.WARNING]
    assert shared[0].text == (
        f"Overwriting {FOOTPRINT} in {SHARED} also changes it for "
        "PARTA (Atomic_Battery_Management), PARTB (Atomic_Battery_Management)"
    )
    assert any(op.kind == "footprint" for op in plan.ops)


def test_an_unresolved_conflict_gives_no_overwrite_warning(atomic_custom, ul_package, tmp_path):
    _, candidate = ul_package
    _clash(atomic_custom, candidate, tmp_path)
    _library_linking(atomic_custom, BATTERY_CHARGER, [("PARTA", LINK)])

    plan = build_plan(candidate, InstallOptions(library=ABSENT_LIBRARY, description=UL_DESCRIPTION), atomic_custom, ToolContext())
    assert not [i for i in plan.issues if i.code == "install.footprint_shared"]


def test_the_part_being_installed_and_other_footprints_are_not_listed(atomic_custom, ul_package, tmp_path):
    _, candidate = ul_package
    _clash(atomic_custom, candidate, tmp_path)
    # CSD85301Q2 in the target library is the part being installed; PARTA links another footprint
    _library_linking(atomic_custom, ABSENT_LIBRARY, [(SYMBOL, LINK)])
    _library_linking(atomic_custom, BATTERY_CHARGER, [("PARTA", f"{LINK}_OTHER"), ("PARTB", LINK)])

    options = InstallOptions(library=ABSENT_LIBRARY, description=UL_DESCRIPTION, resolutions={FP_KEY: Resolution("overwrite")})
    plan = build_plan(candidate, options, atomic_custom, ToolContext())
    conflict = next(c for c in plan.conflicts if c.kind == "footprint")
    assert conflict.existing.endswith("; it is linked by 1 other part: PARTB (Atomic_Battery_Management)")
    shared = next(i for i in plan.issues if i.code == "install.footprint_shared")
    assert "PARTA" not in shared.text and SYMBOL not in shared.text


def test_more_than_twenty_linking_parts_are_cut_short(atomic_custom, ul_package, tmp_path):
    _, candidate = ul_package
    _clash(atomic_custom, candidate, tmp_path)
    _library_linking(atomic_custom, BATTERY_CHARGER, [(f"PART{n:02d}", LINK) for n in range(23)])

    plan = build_plan(candidate, InstallOptions(library=ABSENT_LIBRARY, description=UL_DESCRIPTION), atomic_custom, ToolContext())
    conflict = next(c for c in plan.conflicts if c.kind == "footprint")
    assert "linked by 23 other parts: PART00 (Atomic_Battery_Management)" in conflict.existing
    assert conflict.existing.endswith(", and 3 more")


def test_a_conflict_with_no_linking_part_keeps_the_plain_text(atomic_custom, ul_package, tmp_path):
    _, candidate = ul_package
    _clash(atomic_custom, candidate, tmp_path)

    options = InstallOptions(library=ABSENT_LIBRARY, description=UL_DESCRIPTION, resolutions={FP_KEY: Resolution("overwrite")})
    plan = build_plan(candidate, options, atomic_custom, ToolContext())
    conflict = next(c for c in plan.conflicts if c.kind == "footprint")
    assert conflict.existing == f"{SHARED}.pretty already holds a different {FOOTPRINT}.kicad_mod"
    assert not [i for i in plan.issues if i.code == "install.footprint_shared"]


def test_the_rename_suggestion_moves_on_when_the_part_number_name_is_taken(atomic_custom, ul_package, tmp_path):
    _, candidate = ul_package
    installed = _clash(atomic_custom, candidate, tmp_path)
    taken = installed.with_name(f"{FOOTPRINT}_{SYMBOL}.kicad_mod")
    taken.write_bytes(installed.read_bytes())

    plan = build_plan(candidate, InstallOptions(library=ABSENT_LIBRARY, description=UL_DESCRIPTION), atomic_custom, ToolContext())
    conflict = next(c for c in plan.conflicts if c.kind == "footprint")
    assert conflict.suggested_name == f"{FOOTPRINT}_{SYMBOL}_2"


def test_a_model_conflict_still_suggests_the_next_numbered_name(atomic_custom, ul_package, tmp_path):
    _, candidate = ul_package
    _install_first(atomic_custom, candidate, tmp_path)
    model = next(atomic_custom.models_dir.glob(f"{SYMBOL}.*"))
    model.write_bytes(model.read_bytes() + b"changed")

    plan = build_plan(candidate, InstallOptions(library=ABSENT_LIBRARY, description=UL_DESCRIPTION), atomic_custom, ToolContext())
    conflict = next(c for c in plan.conflicts if c.kind == "model")
    assert conflict.suggested_name == f"{model.stem}_2{model.suffix}"
