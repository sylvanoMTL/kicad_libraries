"""Tracer: the Ultra Librarian sample installed into a tmp_path copy of Custom/ (Phase 4, plan 01)."""

import hashlib
from pathlib import Path

from kicad_lib_manager import fsutil
from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.plan import MODEL_DIR_VAR, InstallOptions
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.kicad_files import (
    find_models,
    find_property,
    find_symbol,
    find_symbols,
    footprint_name,
    load,
)
from kicad_lib_manager.models import Severity
from kicad_lib_manager.sexpr import unquote

REPO_ROOT = Path(__file__).resolve().parent.parent
LIBRARY = "IC_Battery_Charger_TI"


def _hidden(prop) -> bool:
    """True when the property carries a bare hide atom (KiCad 6/7 form) anywhere below it."""
    stack = [prop.node]
    while stack:
        node = stack.pop()
        if node.kind == "atom" and node.text == "hide":
            return True
        stack.extend(node.children)
    return False


def _value_text(footprint_node):
    for child in footprint_node.children:
        if child.head == "fp_text" and child.children[1].text == "value":
            return child.children[2]
    return None


def test_ul_symbol_added_others_identical(custom_copy, ul_package, tmp_path, snapshot):
    package, candidate = ul_package
    layout = custom_copy
    sym_path = layout.symbols_dir / f"{LIBRARY}.kicad_sym"
    original = sym_path.read_bytes()
    original_loaded = load(sym_path)
    previous_end = find_symbols(original_loaded.root)[-1].node.end
    real_before = snapshot(REPO_ROOT / "Custom" / "Symbols") | snapshot(REPO_ROOT / "Custom" / "Footprints")

    plan = build_plan(candidate, InstallOptions(library=LIBRARY), layout)
    assert not plan.blocked, plan.issues
    result = apply_plan(plan, backup_root=tmp_path / "bk")

    assert result.ok, result.issues
    assert not [i for i in result.issues if i.severity is Severity.ERROR]
    pretty = layout.footprints_dir / f"{LIBRARY}.pretty"
    assert result.touched == (
        layout.models_dir / "CSD85301Q2.stp",
        pretty / "DQK0006B.kicad_mod",
        sym_path,
    )

    # Header and every other symbol are byte-identical: removing the inserted segment restores the file
    written = load(sym_path)
    new_node = find_symbol(written.root, "CSD85301Q2").node
    text = written.source.text
    restored = text[:previous_end] + text[new_node.end:]
    assert fsutil.encode_source(restored, written.source.bom) == original
    assert [s.name for s in find_symbols(written.root)][-1] == "CSD85301Q2"

    footprint = load(pretty / "DQK0006B.kicad_mod")
    ref = footprint_name(footprint.root)
    assert ref.name == "DQK0006B"
    value = _value_text(ref.node)
    assert value.kind == "str" and unquote(value.text) == "DQK0006B"
    models = find_models(ref.node)
    assert [m.path for m in models] == [f"{MODEL_DIR_VAR}/CSD85301Q2.stp"]

    symbol = find_symbol(written.root, "CSD85301Q2")
    assert find_property(symbol.node, "Footprint").value == f"{LIBRARY}:DQK0006B"
    assert find_property(symbol.node, "ki_fp_filters").value == "DQK0006B"
    manufacturer = find_property(symbol.node, "Manufacturer")
    mpn = find_property(symbol.node, "MPN")
    assert (manufacturer.value, mpn.value) == ("TI", "CSD85301Q2")
    assert _hidden(manufacturer) and _hidden(mpn)

    model = layout.models_dir / "CSD85301Q2.stp"
    assert hashlib.sha256(model.read_bytes()).hexdigest() == candidate.models[0].file.sha256

    assert result.backup_dir is not None
    assert result.backup_dir.parent == tmp_path / "bk" / "installs"
    assert (result.backup_dir / f"{LIBRARY}.kicad_sym_backup_1").read_bytes() == original

    # The checkout's own Custom/ was never written
    real_after = snapshot(REPO_ROOT / "Custom" / "Symbols") | snapshot(REPO_ROOT / "Custom" / "Footprints")
    assert real_after == real_before
