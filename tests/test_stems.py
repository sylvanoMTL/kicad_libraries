"""The one name rule of the Atomic_ scheme: stems snapshot, installed union and the verdict (LIB-05, D-07..D-13)."""

from kicad_lib_manager.importer.stems import (
    allowed_stems,
    installed_stems,
    name_verdict,
)


def test_installed_folder_to_allowed_set_to_verdict(tmp_path):
    folder = tmp_path / "symbols"
    folder.mkdir()
    (folder / "Transistor_FET.kicad_sym").write_text("", encoding="utf-8")
    (folder / "Brand_New_Stem.kicad_sym").write_text("", encoding="utf-8")
    (folder / "Simulation_SPICE.sp").write_text("", encoding="utf-8")

    stems = allowed_stems(installed_stems(folder))

    assert "Transistor_FET" in stems
    assert "Brand_New_Stem" in stems
    assert "Simulation_SPICE" not in stems
    assert name_verdict("Atomic_Brand_New_Stem", stems).ok is True
    corrected = name_verdict("atomic_transistor_fet")
    assert corrected.ok is False
    assert corrected.name == "Atomic_Transistor_FET"
    assert corrected.note == "Spelling corrected to Atomic_Transistor_FET"
