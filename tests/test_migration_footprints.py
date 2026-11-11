"""Behaviour tests for the footprint side of the Atomic_ migration (Phase 13 plan 13-10, MIG-02, MIG-03).

Every Custom/ here is built fresh under tmp_path by small local helpers (never the live Custom/),
following the pattern tests/test_migration_e2e.py already established for this phase.
"""

from pathlib import Path
from types import SimpleNamespace

from installfixtures import vendor_footprint
from migrationfixtures import _id_lib, _id_symbol
from zipfixtures import STEP_BYTES

from kicad_lib_manager import kicad_files
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.migration.footprints import SHARED, plan_footprints
from kicad_lib_manager.importer.migration.inventory import read_inventory
from kicad_lib_manager.importer.migration.plan import MigrationChoices, PartChoice
from kicad_lib_manager.importer.plan import MODEL_DIR_VAR

_CTX = SimpleNamespace(kicad_fp_dir=None)


def _key(library: str, name: str) -> tuple[str, str]:
    return (f"Custom/Symbols/{library}.kicad_sym", name)


def _write_symbols(root: Path, library: str, parts: list[tuple[str, str]]) -> None:
    """parts: (symbol name, footprint field value "Lib:FP")."""
    symbols_dir = root / "Custom" / "Symbols"
    symbols_dir.mkdir(parents=True, exist_ok=True)
    syms = [
        _id_symbol(name, [("Reference", "U", False), ("Value", name, False), ("Footprint", footprint, True)])
        for name, footprint in parts
    ]
    (symbols_dir / f"{library}.kicad_sym").write_bytes(_id_lib(syms))


def _write_footprint(
    root: Path, library: str, name: str, *, model: str | None = None, models: tuple[str, ...] = ()
) -> None:
    pretty = root / "Custom" / "Footprints" / f"{library}.pretty"
    pretty.mkdir(parents=True, exist_ok=True)
    (pretty / f"{name}.kicad_mod").write_bytes(vendor_footprint(name, model=model, models=models, eol="\r\n"))


def _write_model(root: Path, name: str, data: bytes = STEP_BYTES) -> None:
    models_dir = root / "Custom" / "3DModels"
    models_dir.mkdir(parents=True, exist_ok=True)
    (models_dir / name).write_bytes(data)


def _layout(root: Path) -> RepoLayout:
    for folder in ("Symbols", "Footprints", "3DModels"):
        (root / "Custom" / folder).mkdir(parents=True, exist_ok=True)
    return RepoLayout.for_repo(root)


def _model_paths(data: bytes) -> list[str]:
    loaded = kicad_files.parse_bytes(data, "x.kicad_mod")
    ref = kicad_files.footprint_name(loaded.root)
    return [m.path for m in kicad_files.find_models(ref.node)]


def _write_op(ops, rel: str):
    return next(op for op in ops if op.kind == "write" and op.rel == rel)


def _has_op(ops, kind: str, rel: str) -> bool:
    return any(op.kind == kind and op.rel == rel for op in ops)


# -- Task 1: shared footprints move once, models take the MPN, multi-model keeps every file ------


def test_shared_footprint_moves_once_and_model_takes_mpn(tmp_path):
    library = "IC_Power_Management_LTC"
    part1, part2 = "LTC2954-1-DFN8", "LTC2954-2-DFN8"
    _write_symbols(
        tmp_path,
        library,
        [(part1, f"{library}:DFN-8_DDB"), (part2, f"{library}:DFN-8_DDB")],
    )
    _write_footprint(tmp_path, library, "DFN-8_DDB", model=f"{MODEL_DIR_VAR}/LTC2954OLD.step")
    _write_model(tmp_path, "LTC2954OLD.step")
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    key1, key2 = _key(library, part1), _key(library, part2)
    mpns = {key1: "LTC2954CDDB-1", key2: "LTC2954IDDB-1"}

    outcome = plan_footprints(inventory, MigrationChoices(), _CTX, mpns=mpns)

    assert outcome.links[key1] == outcome.links[key2] == f"{SHARED}:DFN-8_DDB"
    shared_rel = f"Custom/Footprints/{SHARED}.pretty/DFN-8_DDB.kicad_mod"
    footprint_writes = [op for op in outcome.ops if op.kind == "write" and op.rel == shared_rel]
    assert len(footprint_writes) == 1

    model_write = _write_op(outcome.ops, "Custom/3DModels/LTC2954CDDB-1.step")
    assert model_write.source_rel == "Custom/3DModels/LTC2954OLD.step"
    assert _has_op(outcome.ops, "delete", "Custom/3DModels/LTC2954OLD.step")
    assert ("model", "LTC2954OLD.step", "LTC2954CDDB-1.step") in [
        (r.kind, r.old, r.new) for r in outcome.model_renames
    ]
    assert _model_paths(footprint_writes[0].data) == [f"{MODEL_DIR_VAR}/LTC2954CDDB-1.step"]


def test_model_linked_by_two_footprints_keeps_first_mpn(tmp_path):
    _write_symbols(tmp_path, "LibX", [("PARTX", "LibX:FPX")])
    _write_symbols(tmp_path, "LibY", [("PARTY", "LibY:FPY")])
    _write_footprint(tmp_path, "LibX", "FPX", model=f"{MODEL_DIR_VAR}/SHARED-MODEL.step")
    _write_footprint(tmp_path, "LibY", "FPY", model=f"{MODEL_DIR_VAR}/SHARED-MODEL.step")
    _write_model(tmp_path, "SHARED-MODEL.step")
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    key_x, key_y = _key("LibX", "PARTX"), _key("LibY", "PARTY")
    mpns = {key_x: "MPNX", key_y: "MPNY"}

    outcome = plan_footprints(inventory, MigrationChoices(), _CTX, mpns=mpns)

    assert [
        (r.kind, r.old, r.new) for r in outcome.model_renames
    ] == [("model", "SHARED-MODEL.step", "MPNX.step")]
    model_writes = [op for op in outcome.ops if op.kind == "write" and op.rel == "Custom/3DModels/MPNX.step"]
    assert len(model_writes) == 1

    fpx_data = _write_op(outcome.ops, f"Custom/Footprints/{SHARED}.pretty/FPX.kicad_mod").data
    fpy_data = _write_op(outcome.ops, f"Custom/Footprints/{SHARED}.pretty/FPY.kicad_mod").data
    assert _model_paths(fpx_data) == [f"{MODEL_DIR_VAR}/MPNX.step"]
    assert _model_paths(fpy_data) == [f"{MODEL_DIR_VAR}/MPNX.step"]


def test_case_only_model_rename_keeps_disk_spelling(tmp_path):
    _write_symbols(tmp_path, "LibZ", [("PARTZ", "LibZ:FPZ")])
    _write_footprint(tmp_path, "LibZ", "FPZ", model=f"{MODEL_DIR_VAR}/ABC.STEP")
    _write_model(tmp_path, "ABC.STEP")
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    key = _key("LibZ", "PARTZ")
    outcome = plan_footprints(inventory, MigrationChoices(), _CTX, mpns={key: "abc"})

    assert outcome.model_renames == ()
    assert not any(op.rel.startswith("Custom/3DModels/") for op in outcome.ops)
    data = _write_op(outcome.ops, f"Custom/Footprints/{SHARED}.pretty/FPZ.kicad_mod").data
    assert _model_paths(data) == [f"{MODEL_DIR_VAR}/ABC.STEP"]


def test_multi_model_footprint_keeps_every_file(tmp_path):
    _write_symbols(tmp_path, "LibW", [("PARTW1", "LibW:FPW"), ("PARTW2", "LibW:FPW")])
    _write_footprint(
        tmp_path, "LibW", "FPW", models=(f"{MODEL_DIR_VAR}/M1.step", f"{MODEL_DIR_VAR}/M2.step")
    )
    _write_model(tmp_path, "M1.step")
    _write_model(tmp_path, "M2.step")
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    key1, key2 = _key("LibW", "PARTW1"), _key("LibW", "PARTW2")
    mpns = {key1: "DIFFERENT-MPN-1", key2: "DIFFERENT-MPN-2"}

    outcome = plan_footprints(inventory, MigrationChoices(), _CTX, mpns=mpns)

    assert outcome.model_renames == ()
    assert not any(op.rel.startswith("Custom/3DModels/") for op in outcome.ops)
    data = _write_op(outcome.ops, f"Custom/Footprints/{SHARED}.pretty/FPW.kicad_mod").data
    assert _model_paths(data) == [f"{MODEL_DIR_VAR}/M1.step", f"{MODEL_DIR_VAR}/M2.step"]
    assert outcome.leftovers == ()
    assert not any(i.code.startswith("migration.model") for i in outcome.issues)


def test_blank_mpn_keeps_model_name(tmp_path):
    _write_symbols(tmp_path, "LibA", [("PARTA", "LibA:FPA")])
    _write_symbols(tmp_path, "LibB", [("PARTB", "LibB:FPB")])
    _write_footprint(tmp_path, "LibA", "FPA", model=f"{MODEL_DIR_VAR}/OLDNAME.step")
    _write_footprint(tmp_path, "LibB", "FPB", model=f"{MODEL_DIR_VAR}/OLDNAME2.step")
    _write_model(tmp_path, "OLDNAME.step")
    _write_model(tmp_path, "OLDNAME2.step")
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    key_a, key_b = _key("LibA", "PARTA"), _key("LibB", "PARTB")
    choices = MigrationChoices(parts={key_b: PartChoice(model_name="CustomName")})
    outcome = plan_footprints(inventory, choices, _CTX, mpns={key_a: "", key_b: ""})

    data_a = _write_op(outcome.ops, f"Custom/Footprints/{SHARED}.pretty/FPA.kicad_mod").data
    assert _model_paths(data_a) == [f"{MODEL_DIR_VAR}/OLDNAME.step"]
    assert not _has_op(outcome.ops, "write", "Custom/3DModels/OLDNAME.step")

    data_b = _write_op(outcome.ops, f"Custom/Footprints/{SHARED}.pretty/FPB.kicad_mod").data
    assert _model_paths(data_b) == [f"{MODEL_DIR_VAR}/CustomName.step"]
    assert _has_op(outcome.ops, "write", "Custom/3DModels/CustomName.step")
    assert ("model", "OLDNAME2.step", "CustomName.step") in [
        (r.kind, r.old, r.new) for r in outcome.model_renames
    ]
