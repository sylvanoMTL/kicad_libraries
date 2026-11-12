"""Behaviour tests for the footprint side of the Atomic_ migration (Phase 13 plan 13-10, MIG-02, MIG-03).

Every Custom/ here is built fresh under tmp_path by small local helpers (never the live Custom/),
following the pattern tests/test_migration_e2e.py already established for this phase.
"""

from pathlib import Path
from types import SimpleNamespace

from customfixtures import OFFICIAL_FOOTPRINT, OFFICIAL_LIBRARY, OFFICIAL_PADS, write_fake_kicad
from fakecli import FakeCli
from installfixtures import vendor_footprint
from migrationfixtures import _id_lib, _id_symbol
from zipfixtures import STEP_BYTES

from kicad_lib_manager import kicad_files
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.migration.footprints import CLASH_PREFIX, SHARED, plan_footprints
from kicad_lib_manager.importer.migration.gate import check_plan, end_state_context
from kicad_lib_manager.importer.migration.inventory import read_inventory
from kicad_lib_manager.importer.migration.planner import build_migration_plan, prepare_context
from kicad_lib_manager.importer.migration.plan import MigrationChoices, PartChoice
from kicad_lib_manager.importer.plan import MODEL_DIR_VAR, Resolution, ToolContext

_CTX = SimpleNamespace(kicad_fp_dir=None)


def _key(library: str, name: str) -> tuple[str, str]:
    return (f"Custom/Symbols/{library}.kicad_sym", name)


def _write_symbols(
    root: Path, library: str, parts: list[tuple[str, str]], *, pins: dict[str, tuple[str, ...]] | None = None
) -> None:
    """parts: (symbol name, footprint field value "Lib:FP"); pins overrides a part's pin numbers."""
    pins = pins or {}
    symbols_dir = root / "Custom" / "Symbols"
    symbols_dir.mkdir(parents=True, exist_ok=True)
    syms = [
        _id_symbol(
            name,
            [("Reference", "U", False), ("Value", name, False), ("Footprint", footprint, True)],
            pins=pins.get(name, ("1", "2")),
        )
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


def _footprint_with_text(
    name: str, *, descr: str = "", tags: str = "", pads: tuple[str, ...] = ("1", "2"), model: str | None = None
) -> bytes:
    """vendor_footprint's bytes with a (descr ...) / (tags ...) line inserted, for footprint-text tests."""
    data = vendor_footprint(name, pads=pads, model=model, eol="\r\n")
    text = data.decode("utf-8")
    insert = ""
    if descr:
        insert += f'\r\n  (descr "{descr}")'
    if tags:
        insert += f'\r\n  (tags "{tags}")'
    marker = '(layer "F.Cu")'
    idx = text.index(marker) + len(marker)
    return (text[:idx] + insert + text[idx:]).encode("utf-8")


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


# -- Task 2: official footprints, leftovers and board features (D-08, D-10, D-21) ----------------


def _leftover(outcome, rel: str):
    return next(row for row in outcome.leftovers if row.rel == rel)


def test_official_switch_links_kicad_footprint(tmp_path):
    footprints_dir, _models_dir = write_fake_kicad(tmp_path)
    _write_symbols(tmp_path, "LibO", [("PARTO", "LibO:FPO")], pins={"PARTO": OFFICIAL_PADS})
    _write_footprint(tmp_path, "LibO", "FPO", model=f"{MODEL_DIR_VAR}/FPO.step")
    _write_model(tmp_path, "FPO.step")
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    key = _key("LibO", "PARTO")
    official_link = f"{OFFICIAL_LIBRARY}:{OFFICIAL_FOOTPRINT}"
    choices = MigrationChoices(
        parts={key: PartChoice(footprint_target="official", official_footprint=official_link)}
    )
    ctx = SimpleNamespace(kicad_fp_dir=footprints_dir)

    outcome = plan_footprints(inventory, choices, ctx, mpns={key: "PARTO"})

    assert outcome.links[key] == official_link
    assert outcome.targets[key] == "official"
    kicad_root = footprints_dir.parent
    assert not any(op.path.is_relative_to(kicad_root) for op in outcome.ops)
    assert not any(i.severity.value == "error" for i in outcome.issues)

    fp_row = _leftover(outcome, "Custom/Footprints/LibO.pretty/FPO.kicad_mod")
    assert fp_row.default_keep is False
    assert fp_row.keep is False
    assert official_link in fp_row.reason

    model_row = _leftover(outcome, "Custom/3DModels/FPO.step")
    assert model_row.default_keep is False
    assert model_row.keep is False
    assert official_link in model_row.reason


def test_official_pad_mismatch_is_amber(tmp_path):
    footprints_dir, _models_dir = write_fake_kicad(tmp_path)
    pins = tuple(str(n) for n in range(1, 9))
    _write_symbols(tmp_path, "LibM", [("PARTM", "LibM:FPM")], pins={"PARTM": pins})
    _write_footprint(tmp_path, "LibM", "FPM")
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    key = _key("LibM", "PARTM")
    official_link = f"{OFFICIAL_LIBRARY}:{OFFICIAL_FOOTPRINT}"
    choices = MigrationChoices(
        parts={key: PartChoice(footprint_target="official", official_footprint=official_link)}
    )
    ctx = SimpleNamespace(kicad_fp_dir=footprints_dir)

    outcome = plan_footprints(inventory, choices, ctx, mpns={key: "PARTM"})

    warnings = [i for i in outcome.issues if i.code == "migration.pad_mismatch"]
    assert len(warnings) == 1
    assert warnings[0].severity.value == "warning"
    assert not any(i.severity.value == "error" for i in outcome.issues)


def test_official_link_must_exist(tmp_path):
    _write_symbols(tmp_path, "LibN", [("PARTN", "LibN:FPN")])
    _write_footprint(tmp_path, "LibN", "FPN")
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    key = _key("LibN", "PARTN")
    choices = MigrationChoices(
        parts={key: PartChoice(footprint_target="official", official_footprint="Nope_Library:NOPE-FP")}
    )

    outcome = plan_footprints(inventory, choices, _CTX, mpns={key: "PARTN"})

    assert any(i.code == "migration.official_missing" and i.severity.value == "error" for i in outcome.issues)


def test_board_feature_defaults_to_keep(tmp_path):
    (tmp_path / "Custom" / "Footprints" / f"{SHARED}.pretty").mkdir(parents=True, exist_ok=True)
    _write_footprint(tmp_path, SHARED, "BOARD-FEATURE-SHARED")
    _write_footprint(tmp_path, "LibP", "BOARD-FEATURE-V1")
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    outcome = plan_footprints(inventory, MigrationChoices(), _CTX, mpns={})

    shared_row = _leftover(outcome, f"Custom/Footprints/{SHARED}.pretty/BOARD-FEATURE-SHARED.kicad_mod")
    assert shared_row.default_keep is True
    assert shared_row.keep is True
    assert not any(
        op.rel == f"Custom/Footprints/{SHARED}.pretty/BOARD-FEATURE-SHARED.kicad_mod" for op in outcome.ops
    )

    v1_rel = "Custom/Footprints/LibP.pretty/BOARD-FEATURE-V1.kicad_mod"
    v1_row = _leftover(outcome, v1_rel)
    assert v1_row.default_keep is True
    assert v1_row.keep is True
    assert _has_op(outcome.ops, "write", f"Custom/Footprints/{SHARED}.pretty/BOARD-FEATURE-V1.kicad_mod")
    assert _has_op(outcome.ops, "delete", v1_rel)

    choices = MigrationChoices(leftovers={v1_rel: False})
    outcome2 = plan_footprints(inventory, choices, _CTX, mpns={})
    row2 = _leftover(outcome2, v1_rel)
    assert row2.keep is False
    assert _has_op(outcome2.ops, "delete", v1_rel)
    assert not _has_op(outcome2.ops, "write", f"Custom/Footprints/{SHARED}.pretty/BOARD-FEATURE-V1.kicad_mod")


def test_kept_leftover_footprint_moves(tmp_path):
    footprints_dir, _models_dir = write_fake_kicad(tmp_path)
    _write_symbols(tmp_path, "LibO", [("PARTO", "LibO:FPO")], pins={"PARTO": OFFICIAL_PADS})
    _write_footprint(tmp_path, "LibO", "FPO", model=f"{MODEL_DIR_VAR}/FPO.step")
    _write_model(tmp_path, "FPO.step")
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    key = _key("LibO", "PARTO")
    official_link = f"{OFFICIAL_LIBRARY}:{OFFICIAL_FOOTPRINT}"
    fp_rel = "Custom/Footprints/LibO.pretty/FPO.kicad_mod"
    model_rel = "Custom/3DModels/FPO.step"
    choices = MigrationChoices(
        parts={key: PartChoice(footprint_target="official", official_footprint=official_link)},
        leftovers={fp_rel: True, model_rel: True},
    )
    ctx = SimpleNamespace(kicad_fp_dir=footprints_dir)

    outcome = plan_footprints(inventory, choices, ctx, mpns={key: "PARTO"})

    assert _has_op(outcome.ops, "write", f"Custom/Footprints/{SHARED}.pretty/FPO.kicad_mod")
    assert _has_op(outcome.ops, "delete", fp_rel)
    assert not any(op.rel == model_rel for op in outcome.ops)
    assert not any(op.rel.startswith("Custom/3DModels/") for op in outcome.ops)


def test_emptied_pretty_folder_removed(tmp_path):
    _write_symbols(tmp_path, "LibQ", [("PARTQ", "LibQ:FPQ")])
    _write_footprint(tmp_path, "LibQ", "FPQ")
    _write_footprint(tmp_path, "LibQ", "FEATUREQ")
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    key = _key("LibQ", "PARTQ")
    outcome = plan_footprints(inventory, MigrationChoices(), _CTX, mpns={key: "PARTQ"})

    assert _has_op(outcome.ops, "rmdir", "Custom/Footprints/LibQ.pretty")
    assert "Custom/Footprints/LibQ.pretty" in outcome.removed_folders


# -- Task 3: Atomic_Footprints clashes, footprint text and added 3D models (D-07, D-11) ----------


def test_identical_footprint_is_reused(tmp_path):
    """Running the migration a second time (first run's output already on disk) reuses it, no write."""
    _write_symbols(tmp_path, "LibC", [("PARTC", "LibC:FPC")])
    _write_footprint(tmp_path, "LibC", "FPC")
    layout = _layout(tmp_path)
    key = _key("LibC", "PARTC")
    shared_rel = f"Custom/Footprints/{SHARED}.pretty/FPC.kicad_mod"

    first = plan_footprints(read_inventory(layout), MigrationChoices(), _CTX, mpns={key: "PARTC"})
    first_data = _write_op(first.ops, shared_rel).data
    (tmp_path / "Custom" / "Footprints" / f"{SHARED}.pretty").mkdir(parents=True, exist_ok=True)
    (tmp_path / shared_rel).write_bytes(first_data)

    outcome = plan_footprints(read_inventory(layout), MigrationChoices(), _CTX, mpns={key: "PARTC"})

    assert outcome.links[key] == f"{SHARED}:FPC"
    assert not any(op.kind == "write" and op.rel == shared_rel for op in outcome.ops)
    assert _has_op(outcome.ops, "delete", "Custom/Footprints/LibC.pretty/FPC.kicad_mod")
    assert outcome.conflicts == ()


def test_different_footprint_clash_asks(tmp_path):
    (tmp_path / "Custom" / "Footprints" / f"{SHARED}.pretty").mkdir(parents=True, exist_ok=True)
    (tmp_path / "Custom" / "Footprints" / f"{SHARED}.pretty" / "FPD.kicad_mod").write_bytes(
        vendor_footprint("FPD", pads=("1", "2"), eol="\n")
    )
    _write_symbols(tmp_path, "LibD", [("PARTD", "LibD:FPD")])
    _write_footprint(tmp_path, "LibD", "FPD")
    (tmp_path / "Custom" / "Footprints" / "LibD.pretty" / "FPD.kicad_mod").write_bytes(
        vendor_footprint("FPD", pads=("1", "2", "3"), eol="\r\n")
    )
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    key = _key("LibD", "PARTD")
    shared_rel = f"Custom/Footprints/{SHARED}.pretty/FPD.kicad_mod"
    clash_key = f"{CLASH_PREFIX}FPD"

    outcome = plan_footprints(inventory, MigrationChoices(), _CTX, mpns={key: "PARTD"})
    assert any(c.key == clash_key and c.kind == "footprint" and c.suggested_name == "FPD_PARTD" for c in outcome.conflicts)
    assert any(i.code == "migration.conflict_unresolved" for i in outcome.issues)
    assert not any(op.kind == "write" and op.rel == shared_rel for op in outcome.ops)

    rename_choices = MigrationChoices(resolutions={clash_key: Resolution(action="rename")})
    renamed = plan_footprints(inventory, rename_choices, _CTX, mpns={key: "PARTD"})
    assert renamed.links[key] == f"{SHARED}:FPD_PARTD"
    assert _has_op(renamed.ops, "write", f"Custom/Footprints/{SHARED}.pretty/FPD_PARTD.kicad_mod")

    overwrite_choices = MigrationChoices(resolutions={clash_key: Resolution(action="overwrite")})
    overwritten = plan_footprints(inventory, overwrite_choices, _CTX, mpns={key: "PARTD"})
    assert overwritten.links[key] == f"{SHARED}:FPD"
    assert _has_op(overwritten.ops, "write", shared_rel)

    skip_choices = MigrationChoices(resolutions={clash_key: Resolution(action="skip")})
    skipped = plan_footprints(inventory, skip_choices, _CTX, mpns={key: "PARTD"})
    assert skipped.links[key] == f"{SHARED}:FPD"
    assert not any(op.kind == "write" and op.rel == shared_rel for op in skipped.ops)
    assert _has_op(skipped.ops, "delete", "Custom/Footprints/LibD.pretty/FPD.kicad_mod")


def test_footprint_text_generated_and_merged(tmp_path):
    _write_symbols(tmp_path, "LibE", [("PARTE", "LibE:FPE")])
    pretty = tmp_path / "Custom" / "Footprints" / "LibE.pretty"
    pretty.mkdir(parents=True, exist_ok=True)
    (pretty / "FPE.kicad_mod").write_bytes(
        _footprint_with_text("FPE", descr="DFN-8 package, TI", tags="vendortag")
    )
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    key = _key("LibE", "PARTE")
    outcome = plan_footprints(inventory, MigrationChoices(), _CTX, mpns={key: "PARTE"})

    data = _write_op(outcome.ops, f"Custom/Footprints/{SHARED}.pretty/FPE.kicad_mod").data
    loaded = kicad_files.parse_bytes(data, "FPE.kicad_mod")
    ref = kicad_files.footprint_name(loaded.root)
    descr_node = kicad_files.footprint_text_node(ref.node, "descr")
    tags_node = kicad_files.footprint_text_node(ref.node, "tags")
    new_descr = kicad_files.unquote(descr_node.text)
    new_tags = kicad_files.unquote(tags_node.text)

    assert new_descr != "DFN-8 package, TI"
    assert "vendortag" in new_tags.split()

    footprint_changes = [c for c in outcome.field_changes[key] if c.scope == "footprint"]
    descr_changes = [c for c in footprint_changes if c.field == "descr"]
    assert len(descr_changes) == 1
    assert descr_changes[0].old == "DFN-8 package, TI"
    assert descr_changes[0].new == new_descr

    generated_text, written_text = outcome.texts[key]
    assert generated_text.fp_description == new_descr
    assert written_text.fp_description == new_descr

    choices = MigrationChoices(parts={key: PartChoice(fp_description="Typed description", fp_tags="typed tag")})
    outcome2 = plan_footprints(inventory, choices, _CTX, mpns={key: "PARTE"})
    data2 = _write_op(outcome2.ops, f"Custom/Footprints/{SHARED}.pretty/FPE.kicad_mod").data
    loaded2 = kicad_files.parse_bytes(data2, "FPE.kicad_mod")
    ref2 = kicad_files.footprint_name(loaded2.root)
    descr2 = kicad_files.unquote(kicad_files.footprint_text_node(ref2.node, "descr").text)
    tags2 = kicad_files.unquote(kicad_files.footprint_text_node(ref2.node, "tags").text)
    assert descr2 == "Typed description"
    assert tags2 == "typed tag"


def test_added_model_is_linked(tmp_path):
    _write_symbols(tmp_path, "LibF", [("PARTF", "LibF:FPF")])
    _write_footprint(tmp_path, "LibF", "FPF")
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    external = tmp_path / "external"
    external.mkdir(parents=True, exist_ok=True)
    model_source = external / "x.step"
    model_source.write_bytes(STEP_BYTES)

    key = _key("LibF", "PARTF")
    choices = MigrationChoices(parts={key: PartChoice(model_source=str(model_source))})

    outcome = plan_footprints(inventory, choices, _CTX, mpns={key: "PARTF"})

    model_write = _write_op(outcome.ops, "Custom/3DModels/PARTF.step")
    assert model_write.data == STEP_BYTES

    data = _write_op(outcome.ops, f"Custom/Footprints/{SHARED}.pretty/FPF.kicad_mod").data
    assert _model_paths(data) == [f"{MODEL_DIR_VAR}/PARTF.step"]

    bad_choices = MigrationChoices(
        parts={key: PartChoice(model_source=str(external / "does-not-exist.step"))}
    )
    bad_outcome = plan_footprints(inventory, bad_choices, _CTX, mpns={key: "PARTF"})
    assert any(i.code == "migration.model_unreadable" and i.severity.value == "error" for i in bad_outcome.issues)


# -- Gap CR-01 (13-21): the claimed-name registry catches a second claim on one model file name --


def test_colliding_model_names_queue_no_write(tmp_path):
    _write_symbols(tmp_path, "LibG", [("PARTG", "LibG:FPG")])
    _write_symbols(tmp_path, "LibH", [("PARTH", "LibH:FPH")])
    _write_footprint(tmp_path, "LibG", "FPG", model=f"{MODEL_DIR_VAR}/OLD1.step")
    _write_footprint(tmp_path, "LibH", "FPH", model=f"{MODEL_DIR_VAR}/OLD2.step")
    _write_model(tmp_path, "OLD1.step")
    _write_model(tmp_path, "OLD2.step")
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    key_g, key_h = _key("LibG", "PARTG"), _key("LibH", "PARTH")
    choices = MigrationChoices(
        parts={
            key_g: PartChoice(model_name="COLLIDE"),
            key_h: PartChoice(model_name="COLLIDE"),
        }
    )

    outcome = plan_footprints(inventory, choices, _CTX, mpns={key_g: "", key_h: ""})

    assert outcome.model_renames == ()
    assert not any(op.rel.startswith("Custom/3DModels/") for op in outcome.ops)
    clash_issues = [i for i in outcome.issues if i.code == "migration.model_clash"]
    assert len(clash_issues) == 1
    assert clash_issues[0].severity.value == "error"
    text = clash_issues[0].text
    assert "OLD1.step" in text and "OLD2.step" in text and "COLLIDE.step" in text

    data_g = _write_op(outcome.ops, f"Custom/Footprints/{SHARED}.pretty/FPG.kicad_mod").data
    data_h = _write_op(outcome.ops, f"Custom/Footprints/{SHARED}.pretty/FPH.kicad_mod").data
    assert _model_paths(data_g) == [f"{MODEL_DIR_VAR}/OLD1.step"]
    assert _model_paths(data_h) == [f"{MODEL_DIR_VAR}/OLD2.step"]


def test_colliding_model_names_are_case_insensitive(tmp_path):
    _write_symbols(tmp_path, "LibI", [("PARTI", "LibI:FPI")])
    _write_symbols(tmp_path, "LibJ", [("PARTJ", "LibJ:FPJ")])
    _write_footprint(tmp_path, "LibI", "FPI", model=f"{MODEL_DIR_VAR}/OLD3.step")
    _write_footprint(tmp_path, "LibJ", "FPJ", model=f"{MODEL_DIR_VAR}/OLD4.step")
    _write_model(tmp_path, "OLD3.step")
    _write_model(tmp_path, "OLD4.step")
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    key_i, key_j = _key("LibI", "PARTI"), _key("LibJ", "PARTJ")
    choices = MigrationChoices(
        parts={
            key_i: PartChoice(model_name="COLLIDE"),
            key_j: PartChoice(model_name="collide"),
        }
    )

    outcome = plan_footprints(inventory, choices, _CTX, mpns={key_i: "", key_j: ""})

    assert not any(op.rel.startswith("Custom/3DModels/") for op in outcome.ops)
    clash_issues = [i for i in outcome.issues if i.code == "migration.model_clash"]
    assert len(clash_issues) == 1
    assert clash_issues[0].severity.value == "error"


def test_three_groups_one_name_keeps_the_sorted_first(tmp_path):
    _write_symbols(tmp_path, "LibK", [("PARTK", "LibK:FPK")])
    _write_symbols(tmp_path, "LibL", [("PARTL", "LibL:FPL")])
    _write_symbols(tmp_path, "LibR", [("PARTR", "LibR:FPR")])
    _write_footprint(tmp_path, "LibK", "FPK", model=f"{MODEL_DIR_VAR}/OLDK.step")
    _write_footprint(tmp_path, "LibL", "FPL", model=f"{MODEL_DIR_VAR}/OLDL.step")
    _write_footprint(tmp_path, "LibR", "FPR", model=f"{MODEL_DIR_VAR}/OLDR.step")
    _write_model(tmp_path, "OLDK.step")
    _write_model(tmp_path, "OLDL.step")
    _write_model(tmp_path, "OLDR.step")
    layout = _layout(tmp_path)

    key_k, key_l, key_r = _key("LibK", "PARTK"), _key("LibL", "PARTL"), _key("LibR", "PARTR")
    choices = MigrationChoices(
        parts={
            key_k: PartChoice(model_name="COLLIDE"),
            key_l: PartChoice(model_name="COLLIDE"),
            key_r: PartChoice(model_name="COLLIDE"),
        }
    )
    mpns = {key_k: "", key_l: "", key_r: ""}

    outcome1 = plan_footprints(read_inventory(layout), choices, _CTX, mpns=mpns)
    outcome2 = plan_footprints(read_inventory(layout), choices, _CTX, mpns=mpns)

    for outcome in (outcome1, outcome2):
        assert not any(op.rel.startswith("Custom/3DModels/") for op in outcome.ops)
        clash_issues = [i for i in outcome.issues if i.code == "migration.model_clash"]
        assert len(clash_issues) == 1
        assert "OLDK.step" in clash_issues[0].text and "OLDL.step" in clash_issues[0].text

    assert outcome1.issues == outcome2.issues


def test_model_clash_line_is_plain_and_single(tmp_path):
    _write_symbols(tmp_path, "LibG", [("PARTG", "LibG:FPG")])
    _write_symbols(tmp_path, "LibH", [("PARTH", "LibH:FPH")])
    _write_footprint(tmp_path, "LibG", "FPG", model=f"{MODEL_DIR_VAR}/OLD1.step")
    _write_footprint(tmp_path, "LibH", "FPH", model=f"{MODEL_DIR_VAR}/OLD2.step")
    _write_model(tmp_path, "OLD1.step")
    _write_model(tmp_path, "OLD2.step")
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    key_g, key_h = _key("LibG", "PARTG"), _key("LibH", "PARTH")
    choices = MigrationChoices(
        parts={
            key_g: PartChoice(model_name="COLLIDE"),
            key_h: PartChoice(model_name="COLLIDE"),
        }
    )

    outcome = plan_footprints(inventory, choices, _CTX, mpns={key_g: "", key_h: ""})

    clash_issues = [i for i in outcome.issues if i.code == "migration.model_clash"]
    assert len(clash_issues) == 1
    text = clash_issues[0].text
    assert "migration." not in text
    assert "ki_" not in text
    assert "${" not in text
    assert "different" in text and "name" in text


def test_two_models_resolving_to_one_name_block_run(tmp_path):
    _write_symbols(tmp_path, "LibG", [("PARTG", "LibG:FPG")])
    _write_symbols(tmp_path, "LibH", [("PARTH", "LibH:FPH")])
    _write_footprint(tmp_path, "LibG", "FPG", model=f"{MODEL_DIR_VAR}/OLD1.step")
    _write_footprint(tmp_path, "LibH", "FPH", model=f"{MODEL_DIR_VAR}/OLD2.step")
    _write_model(tmp_path, "OLD1.step")
    _write_model(tmp_path, "OLD2.step")
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    key_g, key_h = _key("LibG", "PARTG"), _key("LibH", "PARTH")
    choices = MigrationChoices(
        parts={
            key_g: PartChoice(library="Atomic_Test", model_name="COLLIDE"),
            key_h: PartChoice(library="Atomic_Test", model_name="COLLIDE"),
        }
    )

    tools = ToolContext(kicad_cli=Path("kicad-cli"), cli_runner=FakeCli())
    ctx = prepare_context(inventory, tools, None, today="2026-11-12")
    plan = build_migration_plan(inventory, choices, ctx)

    assert any(i.code == "migration.model_clash" and i.severity.value == "error" for i in plan.issues)
    write_rels = [op.rel for op in plan.ops if op.kind == "write"]
    assert len(write_rels) == len(set(write_rels))

    gate_ctx = end_state_context(plan, inventory, None)
    outcome = check_plan(plan, inventory, gate_ctx)

    assert outcome.run_enabled is False
    first_line = outcome.lines[0]
    assert first_line.key is None
    assert first_line.target is None


def test_added_model_cannot_take_an_existing_model_name(tmp_path):
    _write_symbols(tmp_path, "LibG", [("PARTG", "LibG:FPG")])
    _write_footprint(tmp_path, "LibG", "FPG")
    _write_model(tmp_path, "TAKEN.step")
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    external = tmp_path / "external"
    external.mkdir(parents=True, exist_ok=True)
    model_source = external / "x.step"
    model_source.write_bytes(STEP_BYTES)

    key = _key("LibG", "PARTG")
    choices = MigrationChoices(parts={key: PartChoice(model_source=str(model_source), model_name="TAKEN")})

    outcome = plan_footprints(inventory, choices, _CTX, mpns={key: "PARTG"})

    clash_issues = [i for i in outcome.issues if i.code == "migration.model_clash"]
    assert len(clash_issues) == 1
    assert clash_issues[0].severity.value == "error"
    assert not _has_op(outcome.ops, "write", "Custom/3DModels/TAKEN.step")

    data = _write_op(outcome.ops, f"Custom/Footprints/{SHARED}.pretty/FPG.kicad_mod").data
    assert _model_paths(data) == []
    assert (tmp_path / "Custom" / "3DModels" / "TAKEN.step").read_bytes() == STEP_BYTES


def test_in_run_footprint_overwrite_is_refused(tmp_path):
    _write_symbols(tmp_path, "LibG", [("PARTG", "LibG:FPSHARED")])
    _write_symbols(tmp_path, "LibH", [("PARTH", "LibH:FPSHARED")])
    _write_footprint(tmp_path, "LibG", "FPSHARED")
    pretty_h = tmp_path / "Custom" / "Footprints" / "LibH.pretty"
    pretty_h.mkdir(parents=True, exist_ok=True)
    (pretty_h / "FPSHARED.kicad_mod").write_bytes(vendor_footprint("FPSHARED", pads=("1", "2", "3"), eol="\r\n"))
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    key_g, key_h = _key("LibG", "PARTG"), _key("LibH", "PARTH")
    clash_key = f"{CLASH_PREFIX}FPSHARED"
    choices = MigrationChoices(resolutions={clash_key: Resolution(action="overwrite")})

    outcome = plan_footprints(inventory, choices, _CTX, mpns={key_g: "PARTG", key_h: "PARTH"})

    shared_rel = f"Custom/Footprints/{SHARED}.pretty/FPSHARED.kicad_mod"
    write_ops = [op for op in outcome.ops if op.kind == "write" and op.rel == shared_rel]
    assert len(write_ops) == 1
    assert write_ops[0].data.count(b"(pad ") == 2  # LibG's pad count (2), not LibH's (3)

    refused_issues = [i for i in outcome.issues if i.code == "migration.overwrite_refused"]
    assert len(refused_issues) == 1
    assert refused_issues[0].severity.value == "error"
    assert "FPSHARED.kicad_mod" in refused_issues[0].text
    assert "Rename" in refused_issues[0].text or "Skip" in refused_issues[0].text

    assert _has_op(outcome.ops, "delete", "Custom/Footprints/LibG.pretty/FPSHARED.kicad_mod")
    assert _has_op(outcome.ops, "delete", "Custom/Footprints/LibH.pretty/FPSHARED.kicad_mod")


# -- Gap CR-01 round 2 (13-22): the existing-model guard is casefolded, not exact-string ---------


def test_model_rename_colliding_by_case_with_an_unlinked_model_keeps_its_name(tmp_path):
    _write_symbols(tmp_path, "LibM", [("PARTM", "LibM:FPM")])
    _write_footprint(tmp_path, "LibM", "FPM", model=f"{MODEL_DIR_VAR}/OLD5.step")
    _write_model(tmp_path, "OLD5.step")
    _write_model(tmp_path, "TAKEN2.STEP")  # unlinked by any footprint
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    key = _key("LibM", "PARTM")
    choices = MigrationChoices(parts={key: PartChoice(model_name="taken2")})
    outcome = plan_footprints(inventory, choices, _CTX, mpns={key: ""})

    assert not any(op.rel.startswith("Custom/3DModels/") for op in outcome.ops)
    assert outcome.model_renames == ()
    kept_issues = [i for i in outcome.issues if i.code == "migration.model_kept_name"]
    assert len(kept_issues) == 1
    assert kept_issues[0].severity.value == "info"
    assert not any(i.code == "migration.model_clash" for i in outcome.issues)

    data = _write_op(outcome.ops, f"Custom/Footprints/{SHARED}.pretty/FPM.kicad_mod").data
    assert _model_paths(data) == [f"{MODEL_DIR_VAR}/OLD5.step"]

    leftover = _leftover(outcome, "Custom/3DModels/TAKEN2.STEP")
    assert leftover.keep is True
    assert not _has_op(outcome.ops, "delete", "Custom/3DModels/TAKEN2.STEP")


def test_model_rename_onto_an_exact_existing_name_keeps_its_name(tmp_path):
    _write_symbols(tmp_path, "LibM", [("PARTM", "LibM:FPM")])
    _write_footprint(tmp_path, "LibM", "FPM", model=f"{MODEL_DIR_VAR}/OLD5.step")
    _write_model(tmp_path, "OLD5.step")
    _write_model(tmp_path, "TAKEN3.STEP")  # unlinked by any footprint, exact-name candidate
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    key = _key("LibM", "PARTM")
    choices = MigrationChoices(parts={key: PartChoice(model_name="TAKEN3")})
    outcome = plan_footprints(inventory, choices, _CTX, mpns={key: ""})

    assert not any(op.rel.startswith("Custom/3DModels/") for op in outcome.ops)
    assert outcome.model_renames == ()
    kept_issues = [i for i in outcome.issues if i.code == "migration.model_kept_name"]
    assert len(kept_issues) == 1
    assert kept_issues[0].severity.value == "info"
    assert not any(i.code == "migration.model_clash" for i in outcome.issues)

    data = _write_op(outcome.ops, f"Custom/Footprints/{SHARED}.pretty/FPM.kicad_mod").data
    assert _model_paths(data) == [f"{MODEL_DIR_VAR}/OLD5.step"]

    leftover = _leftover(outcome, "Custom/3DModels/TAKEN3.STEP")
    assert leftover.keep is True
    assert not _has_op(outcome.ops, "delete", "Custom/3DModels/TAKEN3.STEP")


def test_a_rename_onto_a_model_that_is_itself_renamed_is_kept(tmp_path):
    _write_symbols(tmp_path, "LibN", [("PARTN", "LibN:FPN")])
    _write_symbols(tmp_path, "LibO2", [("PARTO2", "LibO2:FPO2")])
    _write_footprint(tmp_path, "LibN", "FPN", model=f"{MODEL_DIR_VAR}/OLD6.step")
    _write_footprint(tmp_path, "LibO2", "FPO2", model=f"{MODEL_DIR_VAR}/OLD7.STEP")
    _write_model(tmp_path, "OLD6.step")
    _write_model(tmp_path, "OLD7.STEP")
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    key_n, key_o2 = _key("LibN", "PARTN"), _key("LibO2", "PARTO2")
    choices = MigrationChoices(
        parts={
            key_n: PartChoice(model_name="old7"),
            key_o2: PartChoice(model_name="FINAL7"),
        }
    )
    outcome = plan_footprints(inventory, choices, _CTX, mpns={key_n: "", key_o2: ""})

    # The first group's candidate collides with OLD7.STEP, which is itself being renamed away;
    # the guard still refuses the chain and keeps OLD6.step under its own name.
    kept_issues = [i for i in outcome.issues if i.code == "migration.model_kept_name"]
    assert len(kept_issues) == 1
    assert not _has_op(outcome.ops, "write", "Custom/3DModels/old7.step")
    data_n = _write_op(outcome.ops, f"Custom/Footprints/{SHARED}.pretty/FPN.kicad_mod").data
    assert _model_paths(data_n) == [f"{MODEL_DIR_VAR}/OLD6.step"]

    # The second group still renames. Its extension case follows OLD7.STEP's own suffix, as the
    # existing single-group rename path already does (sanitize_filename keeps the input's case).
    assert ("model", "OLD7.STEP", "FINAL7.STEP") in [(r.kind, r.old, r.new) for r in outcome.model_renames]
    assert _has_op(outcome.ops, "write", "Custom/3DModels/FINAL7.STEP")


def test_model_kept_name_note_is_plain_and_single(tmp_path):
    _write_symbols(tmp_path, "LibM", [("PARTM", "LibM:FPM")])
    _write_footprint(tmp_path, "LibM", "FPM", model=f"{MODEL_DIR_VAR}/OLD5.step")
    _write_model(tmp_path, "OLD5.step")
    _write_model(tmp_path, "TAKEN2.STEP")
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    key = _key("LibM", "PARTM")
    choices = MigrationChoices(parts={key: PartChoice(model_name="taken2")})
    outcome = plan_footprints(inventory, choices, _CTX, mpns={key: ""})

    kept_issues = [i for i in outcome.issues if i.code == "migration.model_kept_name"]
    assert len(kept_issues) == 1
    text = kept_issues[0].text
    assert "migration." not in text
    assert "ki_" not in text
    assert "${" not in text
    assert "OLD5.step" in text and "taken2.step" in text


def test_untouched_model_collision_raises_no_blocking_line(tmp_path):
    _write_symbols(tmp_path, "LibM", [("PARTM", "LibM:FPM")])
    _write_footprint(tmp_path, "LibM", "FPM", model=f"{MODEL_DIR_VAR}/OLD5.step")
    _write_model(tmp_path, "OLD5.step")
    _write_model(tmp_path, "TAKEN2.STEP")
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    key = _key("LibM", "PARTM")
    choices = MigrationChoices(parts={key: PartChoice(model_name="taken2")})
    tools = ToolContext(kicad_cli=Path("kicad-cli"), cli_runner=FakeCli())
    ctx = prepare_context(inventory, tools, None, today="2026-11-12")
    plan = build_migration_plan(inventory, choices, ctx)

    assert not any(
        i.severity.value == "error" and i.code.startswith("migration.model") for i in plan.issues
    )

    gate_ctx = end_state_context(plan, inventory, None)
    outcome = check_plan(plan, inventory, gate_ctx)
    assert not any("taken2" in line.text for line in outcome.lines)


def test_different_footprint_clash_asks_still_works(tmp_path):
    """Unchanged regression anchor: a clash against a file already on disk keeps all three choices."""
    (tmp_path / "Custom" / "Footprints" / f"{SHARED}.pretty").mkdir(parents=True, exist_ok=True)
    (tmp_path / "Custom" / "Footprints" / f"{SHARED}.pretty" / "FPZZ.kicad_mod").write_bytes(
        vendor_footprint("FPZZ", pads=("1", "2"), eol="\n")
    )
    _write_symbols(tmp_path, "LibZZ", [("PARTZZ", "LibZZ:FPZZ")])
    _write_footprint(tmp_path, "LibZZ", "FPZZ")
    (tmp_path / "Custom" / "Footprints" / "LibZZ.pretty" / "FPZZ.kicad_mod").write_bytes(
        vendor_footprint("FPZZ", pads=("1", "2", "3"), eol="\r\n")
    )
    layout = _layout(tmp_path)
    inventory = read_inventory(layout)

    key = _key("LibZZ", "PARTZZ")
    clash_key = f"{CLASH_PREFIX}FPZZ"
    overwrite_choices = MigrationChoices(resolutions={clash_key: Resolution(action="overwrite")})

    outcome = plan_footprints(inventory, overwrite_choices, _CTX, mpns={key: "PARTZZ"})

    shared_rel = f"Custom/Footprints/{SHARED}.pretty/FPZZ.kicad_mod"
    assert outcome.links[key] == f"{SHARED}:FPZZ"
    assert _has_op(outcome.ops, "write", shared_rel)
    assert not any(i.code == "migration.overwrite_refused" for i in outcome.issues)
