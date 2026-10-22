"""The six preview sections derived from real plans (plan 05-06, PREV-01, PREV-06, D-07).

Every plan here comes from build_plan over a real package: the UL sample, or a synthetic zip built
with zipfixtures/installfixtures. Layouts are synthetic Custom/ trees in tmp_path, so these tests
run without the Custom submodule. Nothing is written except by the one test that applies a plan.
"""

import dataclasses
from contextlib import contextmanager
from pathlib import Path

import pytest
from fakecli import FakeCli
from installfixtures import target_lib, vendor_footprint, vendor_symbol_lib
from zipfixtures import STEP_BYTES, footprint, make_zip, symbol_lib, write_custom_layout

from kicad_lib_manager.importer import kicad_cli
from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.package import open_package
from kicad_lib_manager.importer.plan import InstallOptions, Resolution, ToolContext
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.importer.preview import FileCounts, file_counts, preview_sections
from kicad_lib_manager.kicad_files import find_models, find_property, find_symbol, footprint_name, parse_bytes
from kicad_lib_manager.models import Issue, Severity

REPO_ROOT = Path(__file__).resolve().parent.parent
UL_LIBRARY = "IC_Battery_Charger_TI"
LIBRARY = "IC_Test_TI"
VENDOR = "PART"
V6, V8, V9 = 20211014, 20231120, 20241209
DATASHEET = {"Datasheet": "https://example.com/part"}
ORDER = ("Files", "Renames", "Path rewrites", "Format", "Conflicts", "Issues")


@pytest.fixture(autouse=True)
def _fresh_cli_cache():
    kicad_cli.clear_cache()
    yield
    kicad_cli.clear_cache()


@pytest.fixture
def ul_layout(tmp_path):
    """A synthetic Custom/ that already holds the IC_Battery_Charger_TI symbol/footprint pair."""
    write_custom_layout(tmp_path, [UL_LIBRARY], [UL_LIBRARY])
    return RepoLayout.for_repo(tmp_path)


@pytest.fixture
def layout(tmp_path):
    write_custom_layout(tmp_path, [LIBRARY], [LIBRARY])
    return RepoLayout.for_repo(tmp_path)


@contextmanager
def _open(tmp_path, members, name="pkg.zip"):
    folder = tmp_path / "src"
    folder.mkdir(exist_ok=True)
    zip_path = make_zip(folder / name, members)
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        yield package, candidate


def _members(symbols=("PART",), footprints=("FP",), models=()):
    members = [("part.kicad_sym", symbol_lib(symbols, props=DATASHEET))]
    members += [(f"{name}.kicad_mod", footprint(name)) for name in footprints]
    members += [(name, STEP_BYTES) for name in models]
    return members


def _tools(fake):
    return ToolContext(kicad_cli=Path("kicad-cli-for-tests.exe"), cli_runner=fake)


def _target_layout(tmp_path, version, names=("EXISTING_A",), *, library=LIBRARY):
    write_custom_layout(tmp_path, [library], [library])
    layout = RepoLayout.for_repo(tmp_path)
    (layout.symbols_dir / f"{library}.kicad_sym").write_bytes(target_lib(version, names))
    return layout


def _sections(plan, candidate, options):
    return {section.name: section for section in preview_sections(plan, candidate, options)}


def _texts(section):
    return [row.text for row in section.rows]


def _ul_plan(ul_package, layout, library=UL_LIBRARY, tools=None, **kwargs):
    _, candidate = ul_package
    options = InstallOptions(library=library, **kwargs)
    plan = build_plan(candidate, options, layout, tools or ToolContext())
    return plan, candidate, options


# -- Files ------------------------------------------------------------------------


def test_rows_ul_first_install(ul_package, ul_layout):
    plan, candidate, options = _ul_plan(ul_package, ul_layout)
    assert not plan.blocked, plan.issues
    sections = _sections(plan, candidate, options)
    files = sections["Files"]
    assert files.title == "Files (3)"
    assert _texts(files) == [
        "+ Custom/3DModels/CSD85301Q2.stp",
        "+ Custom/Footprints/IC_Battery_Charger_TI.pretty/DQK0006B.kicad_mod",
        "~ Custom/Symbols/IC_Battery_Charger_TI.kicad_sym",
    ]
    model, fp, sym = files.rows
    assert model.detail.startswith("new, ") and model.detail.endswith(" KiB")
    assert (fp.detail, sym.detail) == ("new", "modified")
    assert (model.tone, fp.tone, sym.tone) == ("success", "success", "default")
    assert all(row.kind == "file" and row.path is not None and row.op_index is not None for row in files.rows)
    assert file_counts(plan, candidate, options) == FileCounts(new=2, modified=1, unchanged=0)
    assert "DLV0006A.stp → CSD85301Q2.stp" in _texts(sections["Renames"])
    vendor_rename = next(r for r in sections["Renames"].rows if r.text.startswith("DLV0006A.stp"))
    assert vendor_rename.detail == "model file"


def test_rows_reimport_shows_unchanged(ul_package, ul_layout, tmp_path):
    first, candidate, options = _ul_plan(ul_package, ul_layout)
    result = apply_plan(first, backup_root=tmp_path / "backups")
    assert result.ok, result.issues
    plan = build_plan(candidate, options, ul_layout, ToolContext())
    assert plan.is_noop
    files = _sections(plan, candidate, options)["Files"]
    assert _texts(files) == [
        "= Custom/3DModels/CSD85301Q2.stp",
        "= Custom/Footprints/IC_Battery_Charger_TI.pretty/DQK0006B.kicad_mod",
        "= Custom/Symbols/IC_Battery_Charger_TI.kicad_sym",
    ]
    assert [row.detail for row in files.rows] == ["unchanged"] * 3
    assert [row.tone for row in files.rows] == ["muted"] * 3
    assert all(row.op_index is None and row.path is not None for row in files.rows)
    assert file_counts(plan, candidate, options) == FileCounts(new=0, modified=0, unchanged=3)


def test_rows_case_twin_is_conflict_not_unchanged(ul_package, ul_layout):
    twin = ul_layout.footprints_dir / f"{UL_LIBRARY}.pretty" / "dqk0006b.kicad_mod"
    twin.write_bytes(b"(footprint \"different\")\n")
    plan, candidate, options = _ul_plan(ul_package, ul_layout)
    sections = _sections(plan, candidate, options)
    assert not any("DQK0006B.kicad_mod" in text for text in _texts(sections["Files"]))
    assert _texts(sections["Conflicts"]) == ["footprint DQK0006B"]
    assert sections["Conflicts"].rows[0].detail == "Needs a choice"
    assert file_counts(plan, candidate, options) == FileCounts(new=1, modified=1, unchanged=0)


def test_rows_new_library_mkdir(ul_package, ul_layout):
    plan, candidate, options = _ul_plan(ul_package, ul_layout, library="IC_New_TI")
    assert not plan.blocked, plan.issues
    files = _sections(plan, candidate, options)["Files"]
    assert _texts(files) == [
        "+ Custom/Footprints/IC_New_TI.pretty/",
        "+ Custom/3DModels/CSD85301Q2.stp",
        "+ Custom/Footprints/IC_New_TI.pretty/DQK0006B.kicad_mod",
        "+ Custom/Symbols/IC_New_TI.kicad_sym",
    ]
    assert files.rows[0].detail == "new"
    # A folder is not a file: it is listed but never counted
    assert file_counts(plan, candidate, options) == FileCounts(new=3, modified=0, unchanged=0)


def test_rows_refused_plan(ul_package, ul_layout):
    plan, candidate, options = _ul_plan(ul_package, ul_layout, library="IC_SubCategory_TI")
    assert plan.blocked and not plan.symbol_names
    sections = _sections(plan, candidate, options)
    assert sections["Files"].title == "Files (0)"
    assert list(sections) == ["Files", "Issues"]
    first = sections["Issues"].rows[0]
    assert first.text.startswith("✖ ") and first.tone == "error"
    assert file_counts(plan, candidate, options) == FileCounts(0, 0, 0)


def test_rows_new_library_without_model_has_no_model_row(layout, tmp_path):
    with _open(tmp_path, _members()) as (_, candidate):
        options = InstallOptions(library="IC_Single_TI")
        plan = build_plan(candidate, options, layout, ToolContext())
        files = _sections(plan, candidate, options)["Files"]
    assert files.title == "Files (3)"
    assert _texts(files) == [
        "+ Custom/Footprints/IC_Single_TI.pretty/",
        "+ Custom/Footprints/IC_Single_TI.pretty/FP.kicad_mod",
        "+ Custom/Symbols/IC_Single_TI.kicad_sym",
    ]


def test_rows_order_is_fixed_and_repeatable(ul_package, ul_layout):
    plan, candidate, options = _ul_plan(ul_package, ul_layout)
    again = build_plan(candidate, options, ul_layout, ToolContext())
    assert preview_sections(plan, candidate, options) == preview_sections(again, candidate, options)
    kinds = [row.text.split("/")[1] if "/" in row.text else "" for row in _sections(plan, candidate, options)["Files"].rows]
    assert kinds == ["3DModels", "Footprints", "Symbols"]


# -- Path rewrites ------------------------------------------------------------------


def test_rewrites_match_planned_bytes(ul_package, ul_layout):
    plan, candidate, options = _ul_plan(ul_package, ul_layout)
    rewrites = {row.text: row.detail for row in _sections(plan, candidate, options)["Path rewrites"].rows}
    assert list(rewrites) == ["Footprint", "Model", "ki_fp_filters"]

    sym_op = next(op for op in plan.ops if op.kind == "symbol_lib")
    fp_op = next(op for op in plan.ops if op.kind == "footprint")
    symbol = find_symbol(parse_bytes(sym_op.data, "lib").root, plan.symbol_name)
    planned_footprint = find_property(symbol.node, "Footprint").value
    planned_filters = find_property(symbol.node, "ki_fp_filters").value
    planned_model = find_models(footprint_name(parse_bytes(fp_op.data, "fp").root).node)[0].path

    assert rewrites["Footprint"].endswith(f" → {planned_footprint}")
    assert planned_footprint == f"{UL_LIBRARY}:DQK0006B"
    assert rewrites["ki_fp_filters"].endswith(f" → {planned_filters}")
    assert rewrites["Model"] == f"(none) → {planned_model}"
    assert planned_model == "${CUSTOM_3DMODEL_DIR}/CSD85301Q2.stp"
    # The old values are the vendor's own
    vendor_meta = candidate.symbols[0].meta
    assert rewrites["Footprint"].startswith(f"{vendor_meta.footprint_field or '(none)'} → ")
    assert rewrites["ki_fp_filters"].startswith(f"{vendor_meta.fp_filters or '(none)'} → ")


def test_rewrites_without_model_have_no_model_row(layout, tmp_path):
    with _open(tmp_path, _members()) as (_, candidate):
        options = InstallOptions(library=LIBRARY)
        plan = build_plan(candidate, options, layout, ToolContext())
        rewrites = _sections(plan, candidate, options)["Path rewrites"]
    assert _texts(rewrites) == ["Footprint", "ki_fp_filters"]
    assert rewrites.rows[0].detail == f"(none) → {LIBRARY}:FP"


def test_rewrites_skip_a_kept_symbol(tmp_path):
    # The existing PART is kept, so its Footprint and filters are not rewritten and must not be listed
    layout = _target_layout(tmp_path, V6, ("PART",))
    with _open(tmp_path, _members()) as (_, candidate):
        key = f"symbol:{LIBRARY}:PART"
        options = InstallOptions(library=LIBRARY, resolutions={key: Resolution("skip")})
        plan = build_plan(candidate, options, layout, ToolContext())
        assert plan.linked_footprint is None, plan.issues
        sections = _sections(plan, candidate, options)
    assert "Path rewrites" not in sections
    symbol_row = next(r for r in sections["Files"].rows if r.text.endswith(".kicad_sym"))
    assert symbol_row.text.startswith("= ") and symbol_row.detail == "unchanged (kept existing)"
    assert sections["Conflicts"].rows[0].detail == "Skip - keep & link"


# -- Format ---------------------------------------------------------------------------

FORMAT_CASES = [
    pytest.param(
        V9, V6, "fake", "Symbol format 20211014 → 20241209",
        "kicad-cli will normalise the incoming symbol", "", "default", id="normalise",
    ),
    pytest.param(
        V6, V6, None, "Symbol format 20211014 → 20211014",
        "Already in the target format", "", "default", id="already",
    ),
    pytest.param(
        V9, V6, None, "Symbol format 20211014 → 20241209",
        "⚠ kicad-cli not found - symbol merged as-is", "⚠", "warning", id="cli_not_found",
    ),
    pytest.param(
        V9, V6, "differs", "Symbol format 20211014 → 20241209",
        "⚠ Symbol merged as-is - see Issues", "⚠", "warning", id="merged_as_is",
    ),
    pytest.param(
        V6, V9, None, None,
        "✖ Incoming file is newer than the library - refused", "✖", "error", id="newer_refused",
    ),
]


@pytest.mark.parametrize(("target", "vendor", "cli", "row1", "row2", "glyph", "tone"), FORMAT_CASES)
def test_format_rows_cases(tmp_path, target, vendor, cli, row1, row2, glyph, tone):
    layout = _target_layout(tmp_path, target)
    tools = {None: ToolContext(), "fake": _tools(FakeCli()), "differs": _tools(FakeCli(output_version=V8))}[cli]
    members = [
        ("part.kicad_sym", vendor_symbol_lib(VENDOR, version=vendor)),
        ("FP.kicad_mod", vendor_footprint("FP")),
    ]
    with _open(tmp_path, members) as (_, candidate):
        options = InstallOptions(library=LIBRARY)
        plan = build_plan(candidate, options, layout, tools)
        fmt = _sections(plan, candidate, options)["Format"]
    texts = _texts(fmt)
    assert texts[-1] == row2
    assert fmt.rows[-1].glyph == glyph and fmt.rows[-1].tone == tone
    assert all(row.kind == "format" for row in fmt.rows)
    if row1 is None:
        # A refused plan has no versions to show, only the refusal
        assert texts == [row2]
    else:
        assert texts == [row1, row2]


# -- Conflicts ----------------------------------------------------------------------------


def _conflict_plan(layout, tmp_path, resolutions):
    (layout.footprints_dir / f"{LIBRARY}.pretty" / "FP.kicad_mod").write_bytes(footprint("FP", model="old.step"))
    with _open(tmp_path, _members()) as (_, candidate):
        options = InstallOptions(library=LIBRARY, resolutions=resolutions)
        plan = build_plan(candidate, options, layout, ToolContext())
        return plan, _sections(plan, candidate, options), file_counts(plan, candidate, options)


def test_conflict_rows_details(layout, tmp_path):
    key = f"footprint:{LIBRARY}:fp"
    pretty = f"Custom/Footprints/{LIBRARY}.pretty/FP.kicad_mod"

    _, sections, _ = _conflict_plan(layout, tmp_path, {})
    row = sections["Conflicts"].rows[0]
    assert (row.text, row.detail, row.tone, row.kind, row.key) == (
        "footprint FP", "Needs a choice", "warning", "conflict", key,
    )
    assert pretty not in " ".join(_texts(sections["Files"]))

    _, sections, counts = _conflict_plan(layout, tmp_path, {key: Resolution("overwrite")})
    assert sections["Conflicts"].rows[0].detail == "Overwrite"
    assert sections["Conflicts"].rows[0].tone == "default"
    assert f"~ {pretty}" in _texts(sections["Files"])
    assert counts.modified == 2

    plan, sections, _ = _conflict_plan(layout, tmp_path, {key: Resolution("rename", "FP_2")})
    assert sections["Conflicts"].rows[0].detail == "Rename → FP_2"
    assert "FP → FP_2" in _texts(sections["Renames"])
    assert f"+ Custom/Footprints/{LIBRARY}.pretty/FP_2.kicad_mod" in _texts(sections["Files"])
    assert plan.footprint_names == ("FP_2",)

    _, sections, counts = _conflict_plan(layout, tmp_path, {key: Resolution("skip")})
    assert sections["Conflicts"].rows[0].detail == "Skip - keep & link"
    kept = next(r for r in sections["Files"].rows if r.text.endswith("FP.kicad_mod"))
    assert (kept.text, kept.detail, kept.tone) == (f"= {pretty}", "unchanged (kept existing)", "muted")
    assert counts.unchanged == 1


# -- Issues -------------------------------------------------------------------------------


def test_issue_rows_no_model_warning(layout, tmp_path):
    with _open(tmp_path, _members()) as (_, candidate):
        options = InstallOptions(library=LIBRARY)
        plan = build_plan(candidate, options, layout, ToolContext())
        issues = _sections(plan, candidate, options)["Issues"]
    row = next(r for r in issues.rows if "No 3D model found" in r.text)
    assert row.text == "⚠ No 3D model found in pkg.zip; the footprint installs without one"
    assert (row.tone, row.glyph, row.kind) == ("warning", "⚠", "issue")


def test_issue_rows_follow_severity(layout, tmp_path):
    with _open(tmp_path, _members()) as (_, candidate):
        options = InstallOptions(library=LIBRARY)
        plan = build_plan(candidate, options, layout, ToolContext())
    custom = dataclasses.replace(plan, issues=(
        Issue(Severity.ERROR, "x.error", "bad"),
        Issue(Severity.WARNING, "x.warning", "careful"),
        Issue(Severity.SUCCESS, "x.success", "done"),
        Issue(Severity.INFO, "x.info", "fyi"),
    ))
    rows = _sections(custom, candidate, options)["Issues"].rows
    assert [(r.text, r.glyph, r.tone) for r in rows] == [
        ("✖ bad", "✖", "error"),
        ("⚠ careful", "⚠", "warning"),
        ("✓ done", "✓", "success"),
        ("fyi", "", "default"),
    ]


# -- Section order ----------------------------------------------------------------------------


def test_sections_order_and_empty_hidden(layout, tmp_path, ul_package, ul_layout):
    with _open(tmp_path, _members()) as (_, candidate):
        options = InstallOptions(library=LIBRARY)
        plan = build_plan(candidate, options, layout, ToolContext())
        names = [s.name for s in preview_sections(plan, candidate, options)]
    # Nothing is renamed and nothing conflicts, so those sections are hidden
    assert names == ["Files", "Path rewrites", "Format", "Issues"]

    ul_plan, ul_candidate, ul_options = _ul_plan(ul_package, ul_layout)
    ul_names = [s.name for s in preview_sections(ul_plan, ul_candidate, ul_options)]
    positions = [ORDER.index(name) for name in ul_names]
    assert positions == sorted(positions) and ul_names[0] == "Files"
    assert "Renames" in ul_names and "Conflicts" not in ul_names
