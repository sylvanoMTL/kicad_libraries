"""Sibling index and family vote (LIB-04): the stock KiCad tree and the owner's Atomic_ libraries vote a part into a library."""

from customfixtures import atomic_lib, atomic_part
from kicad_lib_manager.importer.siblings import SiblingPick, own_index, pick, stock_index
from stockfixtures import write_stock_sample


def test_csd_part_votes_into_transistor_fet_from_the_stock_tree(tmp_path):
    symbols_dir, _ = write_stock_sample(tmp_path)

    result = pick(stock_index(symbols_dir), "CSD85301Q2")

    # power's CSDPWR never votes; the Diode count stays as an alternative
    assert result == SiblingPick("Transistor_FET", "CSD", (("Transistor_FET", 3), ("Diode", 1)))


def test_csd_part_votes_into_transistor_fet_from_the_owners_atomic_libraries(tmp_path):
    symbols = tmp_path / "Custom" / "Symbols"
    symbols.mkdir(parents=True)
    (symbols / "Atomic_Transistor_FET.kicad_sym").write_bytes(atomic_lib((atomic_part("CSD99999"),)))
    # A v1 name and a hand-made Atomic_ library hold CSD parts too; neither may vote
    (symbols / "IC_PowerManagementMosfet_TI.kicad_sym").write_bytes(atomic_lib((atomic_part("CSD11111"),)))
    (symbols / "Atomic_MyStuff.kicad_sym").write_bytes(atomic_lib((atomic_part("CSD22222"),)))

    result = pick(own_index(symbols), "CSD85301Q2")

    assert result == SiblingPick("Transistor_FET", "CSD", (("Transistor_FET", 1),))
