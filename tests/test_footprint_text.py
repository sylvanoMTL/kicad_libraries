"""What a footprint is and the description and tags made from it (FLD-03, D-28, D-29).

The tracer test runs the Ultra Librarian DQK0006B footprint from the committed zip through the
facts, the sentence, the tags and the write back into the file.
"""

import zipfile

from zipfixtures import UL_FOOTPRINT_MEMBER, UL_ZIP

from kicad_lib_manager.importer import footprint_text as ft
from kicad_lib_manager.kicad_files import LoadedFile, footprint_name, footprint_text_edit, parse_bytes
from kicad_lib_manager.sexpr import apply_edits

UL_CODE = "DQK0006B"
UL_TEXTS = ["Texas WSON-6 DQK, 2x2mm, 0.65mm pitch"]
UL_DESCRIBE = "WSON-6 2.1x2.1 mm, 0.65 mm pitch, TI DQK0006B"
UL_TAGS = ["WSON-6", "WSON-6_2.1x2.1mm_P0.65mm", "DQK0006B", "P0.65mm"]


def _load(data: bytes) -> LoadedFile:
    loaded = parse_bytes(data, "fixture")
    assert isinstance(loaded, LoadedFile), loaded
    return loaded


def ul_footprint_bytes() -> bytes:
    with zipfile.ZipFile(UL_ZIP) as zf:
        return zf.read(UL_FOOTPRINT_MEMBER)


def test_ul_footprint_facts():
    loaded = _load(ul_footprint_bytes())
    node = footprint_name(loaded.root).node
    facts = ft.footprint_facts(node, code=UL_CODE, maker="TI", texts=UL_TEXTS)
    assert facts.pads == 8
    assert facts.pitch == 0.65
    assert facts.body == (2.1, 2.1)
    assert facts.family == "WSON-6"
    assert (facts.code, facts.maker) == (UL_CODE, "TI")


def test_ul_footprint_sentence_and_tags():
    loaded = _load(ul_footprint_bytes())
    node = footprint_name(loaded.root).node
    facts = ft.footprint_facts(node, code=UL_CODE, maker="TI", texts=UL_TEXTS)
    assert ft.describe(facts) == UL_DESCRIBE
    assert ft.ipc_name(facts) == "WSON-6_2.1x2.1mm_P0.65mm"
    assert ft.generated_tags(facts) == UL_TAGS


def test_ul_footprint_text_is_written_back():
    loaded = _load(ul_footprint_bytes())
    node = footprint_name(loaded.root).node
    facts = ft.footprint_facts(node, code=UL_CODE, maker="TI", texts=UL_TEXTS)
    text, eol = loaded.source.text, loaded.source.eol
    edits = [
        footprint_text_edit(text, node, "descr", ft.describe(facts), eol),
        footprint_text_edit(text, node, "tags", " ".join(ft.generated_tags(facts)), eol),
    ]
    out = apply_edits(text, edits)
    after = footprint_name(_load(out.encode("utf-8")).root).node
    assert ft.vendor_texts(after) == (UL_DESCRIBE, " ".join(UL_TAGS))
