"""The gate's reasons in the reason strip: a plain sentence, the control that fixes it, live clearing (D-25, LIB-07).

The form rows run without Qt on a fake plan; the dialog rows open the real UL sample or a synthetic package.
"""

import html
from pathlib import Path

import pytest
from installfixtures import ATOMIC_PROPS
from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from test_import_dialog import core_with, frame_blocked, set_library, strip_links, wait_plan, with_issues
from test_import_form import ERR, fake_plan, pairs, status
from zipfixtures import STEP_BYTES, footprint, make_zip, symbol_lib

from kicad_lib_manager import settings
from kicad_lib_manager.importer.form import ATOMIC_TARGETS, atomic_reason, blocking_reasons
from kicad_lib_manager.models import Issue, Severity
from kicad_lib_manager.widgets.import_dialog import ImportDialog

REPO_ROOT = Path(__file__).resolve().parent.parent
UL_ZIP = REPO_ROOT / "downloaded_examples" / "ul_CSD85301Q2.zip"
ATXK_ZIP = REPO_ROOT / "downloaded_examples" / "ul_ATXK-H14-D-32-768KHZ-E50-T3.zip"
requires_atxk = pytest.mark.skipif(not ATXK_ZIP.exists(), reason="downloaded_examples/ul_ATXK-H14-D-32-768KHZ-E50-T3.zip not present")
LIBRARY = "Atomic_Battery_Management"
NO_MODEL = "3D model: the footprint has no 3D model. Use Add 3D model... or an official KiCad footprint"


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path):
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "qsettings"))
    file_name = Path(settings.get_settings().fileName()).resolve()
    assert tmp_path.resolve() in file_name.parents


def atomic(rule: str, text: str) -> Issue:
    return Issue(ERR, f"install.atomic.{rule}", text)


# -- the tracer: "Type a Description" from the gate to a click that focuses the field --------------------


def test_a_missing_description_reads_type_a_description_and_clears_with_the_text():
    plan = fake_plan(issues=(atomic("description", "no description"),))

    assert pairs(blocking_reasons(status(), plan)) == [("Type a Description", "description")]
    assert pairs(blocking_reasons(status(description_text="x"), plan)) == []


def test_clicking_the_description_reason_focuses_the_field_and_typing_lifts_the_block(qtbot, atomic_custom, tmp_path):
    dialog = ImportDialog(atomic_custom.repo_root, atomic_custom, core=core_with(), backup_root=tmp_path / "backups")
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.open_path(UL_ZIP)
    wait_plan(qtbot, dialog)
    set_library(dialog, LIBRARY, fill=False)
    wait_plan(qtbot, dialog)

    links = strip_links(dialog)
    assert "Type a Description" in links
    assert not dialog._install_btn.isEnabled()
    assert frame_blocked(dialog, "description")

    dialog._on_reason_link(links["Type a Description"])
    assert dialog._field_edits["description"].hasFocus()

    # keyClicks types into the focused field; the reason and the frame go before the rebuild answers
    QTest.keyClicks(dialog._field_edits["description"], "Dual N-channel MOSFET")
    assert "Type a Description" not in strip_links(dialog)
    assert not frame_blocked(dialog, "description")
    qtbot.waitUntil(lambda: dialog._install_btn.isEnabled(), timeout=30000)
    assert dialog._install_btn.isEnabled()


# -- every rule's sentence and target (form level, no Qt) --------------------------------------------------


@pytest.mark.parametrize(
    ("rule", "text", "sentence", "target"),
    [
        ("mpn", "no MPN", "Enter the MPN", "mpn"),
        ("manufacturer", "no manufacturer", "Enter the Manufacturer", "manufacturer"),
        ("datasheet", "no datasheet", "Enter a Datasheet link", "datasheet"),
        (
            "datasheet",
            "Datasheet is not a link or file path",
            "The Datasheet must be a link or a file path",
            "datasheet",
        ),
        ("description", "no description", "Type a Description", "description"),
        ("model_3d", "the footprint has no 3D model", NO_MODEL, "model"),
        (
            "model_3d",
            '3D model "x.step" is not in Custom/3DModels (names are case-sensitive)',
            '3D model: 3D model "x.step" is not in Custom/3DModels (names are case-sensitive). Use Add 3D model... or an official KiCad footprint',
            "model",
        ),
        ("footprint", "no footprint", "Footprint: no footprint", "footprint_name"),
        ("value", 'Value "A" is not the MPN "B"', 'Value: Value "A" is not the MPN "B"', "mpn"),
    ],
)
def test_each_rule_text_has_its_sentence_and_its_field(rule, text, sentence, target):
    reason = atomic_reason(atomic(rule, text))

    assert (reason.text, reason.target) == (sentence, target)
    assert ATOMIC_TARGETS[rule] == target
    if rule not in ("mpn", "value"):  # a typed MPN lifts these two, and a blank one has its own reason
        assert blocking_reasons(status(), fake_plan(issues=(atomic(rule, text),))) == [reason]


def test_an_unknown_text_of_a_rule_reads_label_then_text():
    reason = atomic_reason(atomic("manufacturer", "something new"))

    assert (reason.text, reason.target) == ("Manufacturer: something new", "manufacturer")


def test_failures_come_in_atomic_rules_order_one_per_rule():
    plan = fake_plan(
        issues=(
            atomic("manufacturer", "no manufacturer"),
            atomic("datasheet", "no datasheet"),
            atomic("model_3d", "the footprint has no 3D model"),
        )
    )

    assert pairs(blocking_reasons(status(), plan)) == [
        ("Enter the Manufacturer", "manufacturer"),
        ("Enter a Datasheet link", "datasheet"),
        (NO_MODEL, "model"),
    ]


def test_a_failing_parent_symbol_is_named_and_targets_no_field():
    plan = fake_plan(issues=(atomic("description", "PARENT_X: no description"),))

    assert pairs(blocking_reasons(status(description_text="typed"), plan)) == [
        ("PARENT_X (parent symbol): Type a Description", "plan")
    ]


def test_a_valid_datasheet_link_lifts_the_reason_at_once_and_a_bad_one_does_not():
    plan = fake_plan(issues=(atomic("datasheet", "no datasheet"),))

    assert pairs(blocking_reasons(status(datasheet_text="https://x.example/p.pdf"), plan)) == []
    assert pairs(blocking_reasons(status(datasheet_text="not a link"), plan)) == [
        ("Enter a Datasheet link", "datasheet")
    ]


def test_typing_a_manufacturer_or_an_mpn_lifts_its_reason_at_once():
    plan = fake_plan(issues=(atomic("manufacturer", "no manufacturer"), atomic("value", 'Value "A" is not the MPN "B"')))

    assert pairs(blocking_reasons(status(manufacturer_text=""), plan))[0] == ("Enter the Manufacturer", "manufacturer")
    assert blocking_reasons(status(manufacturer_text="Texas Instruments", mpn_text="CSD85301Q2"), plan) == []


def test_a_blank_mpn_shows_one_reason_not_two():
    plan = fake_plan(issues=(atomic("mpn", "no MPN"),))

    assert pairs(blocking_reasons(status(mpn_text=""), plan)) == [("MPN is empty - it names the 3D model file", "mpn")]


def test_the_unknown_manufacturer_note_never_becomes_a_reason():
    note = Issue(
        Severity.INFO, "install.atomic_note.unknown_manufacturer", 'manufacturer "Acme" is not in the manufacturer table'
    )

    assert blocking_reasons(status(), fake_plan(issues=(note,))) == []


def test_a_rejected_model_source_keeps_its_reason_and_targets_remove():
    reasons = blocking_reasons(status(model_error="m.step holds no usable 3D model"), fake_plan())

    assert pairs(reasons) == [("Error: m.step holds no usable 3D model", "model_rejected")]


def test_no_reason_of_the_gate_shows_a_field_name_or_starts_with_error():
    texts = {
        "mpn": ["no MPN", "no MPN of its own (the parent's MPN does not count)", 'MPN is stored as "ki_mpn", not as "MPN"'],
        "manufacturer": ["no manufacturer", 'Manufacturer is stored in several fields ("ki_manufacturer", "Manufacturer")'],
        "footprint": ["no footprint", 'footprint "F" is not in library "L"'],
        "value": ['Value "A" is not the MPN "B"', 'no Value (it should be the MPN "B")'],
        "datasheet": ["no datasheet", "Datasheet is not a link or file path"],
        "description": ["no description", 'no description (inherited from "ki_description")'],
        "model_3d": [
            "the footprint has no 3D model",
            "Could not check the 3D model: it uses ${ki_fp_filters}",
            '3D model "x.step" is not in Custom/3DModels (names are case-sensitive)',
        ],
    }
    seen = 0
    for rule, rule_texts in texts.items():
        for text in rule_texts:
            for prefix in ("", "PARENT: "):
                reason = atomic_reason(atomic(rule, prefix + text))
                seen += 1
                assert "ki_" not in reason.text, reason.text
                assert not reason.text.startswith("Error:"), reason.text
    assert seen == 32


# -- the dialog: click, focus, amber frame, live clearing -----------------------------------------------------


def open_dialog(qtbot, atomic_custom, tmp_path, members, *, core=None) -> ImportDialog:
    folder = tmp_path / "src"
    folder.mkdir(exist_ok=True)
    zip_path = make_zip(folder / "pkg.zip", members)
    dialog = ImportDialog(
        atomic_custom.repo_root, atomic_custom, core=core or core_with(), backup_root=tmp_path / "backups"
    )
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.open_path(zip_path)
    wait_plan(qtbot, dialog)
    set_library(dialog, LIBRARY, fill=False)
    wait_plan(qtbot, dialog)
    return dialog


def package_members(props=None, *, models=("part.step",)):
    symbol = symbol_lib(("PART",), props=ATOMIC_PROPS if props is None else props)
    return [("part.kicad_sym", symbol), ("FP.kicad_mod", footprint("FP")), *((name, STEP_BYTES) for name in models)]


def test_the_missing_model_reason_focuses_the_visible_add_button_and_frames_it(qtbot, atomic_custom, tmp_path):
    dialog = open_dialog(qtbot, atomic_custom, tmp_path, package_members(models=()))

    links = strip_links(dialog)
    assert NO_MODEL in links
    assert frame_blocked(dialog, "model")
    dialog._on_reason_link(links[NO_MODEL])
    button = dialog._add_model_btn
    assert button.isVisible() and button.isEnabled()
    assert button.hasFocus()
    assert dialog._reason_targets["model"] is button
    assert dialog._reason_targets["model_rejected"] is dialog._remove_model_btn


@requires_atxk
def test_an_empty_library_lists_every_reason_and_the_model_reason_focuses_add_3d_model(qtbot, atomic_custom, tmp_path):
    dialog = ImportDialog(atomic_custom.repo_root, atomic_custom, core=core_with(), backup_root=tmp_path / "backups")
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.open_path(ATXK_ZIP)
    wait_plan(qtbot, dialog)

    # ATXK-H14 asks for a library (owner decision of UAT test 14), so the field stays empty
    assert dialog._library_combo.currentText() == ""
    assert [(r.text, r.target) for r in dialog._strip_reasons] == [
        ("Pick or type a library name", "library"),
        ("Enter the Manufacturer", "manufacturer"),
        ("The Datasheet must be a link or a file path", "datasheet"),
        ("Type a Description", "description"),
        (NO_MODEL, "model"),
    ]
    assert not dialog._install_btn.isEnabled()
    for target in ("library", "manufacturer", "datasheet", "description", "model"):
        assert frame_blocked(dialog, target), target

    dialog._on_reason_link(strip_links(dialog)[NO_MODEL])
    assert dialog._add_model_btn.hasFocus()


def test_manufacturer_and_datasheet_reasons_focus_their_fields_and_clear_as_typed(qtbot, atomic_custom, tmp_path):
    dialog = open_dialog(qtbot, atomic_custom, tmp_path, package_members({"Description": "Test part"}))

    links = strip_links(dialog)
    assert "Enter the Manufacturer" in links and "Enter a Datasheet link" in links
    assert frame_blocked(dialog, "manufacturer") and frame_blocked(dialog, "datasheet")
    dialog._on_reason_link(links["Enter the Manufacturer"])
    assert dialog._field_edits["manufacturer"].hasFocus()
    QTest.keyClicks(dialog._field_edits["manufacturer"], "Texas Instruments")
    assert "Enter the Manufacturer" not in strip_links(dialog)
    assert not frame_blocked(dialog, "manufacturer")
    assert frame_blocked(dialog, "datasheet")

    wait_plan(qtbot, dialog)
    dialog._on_reason_link(strip_links(dialog)["Enter a Datasheet link"])
    assert dialog._field_edits["datasheet"].hasFocus()
    QTest.keyClicks(dialog._field_edits["datasheet"], "not a link")
    wait_plan(qtbot, dialog)
    assert "The Datasheet must be a link or a file path" in strip_links(dialog)
    dialog._field_edits["datasheet"].selectAll()
    QTest.keyClicks(dialog._field_edits["datasheet"], "https://www.ti.com/lit/ds/part.pdf")
    assert "The Datasheet must be a link or a file path" not in strip_links(dialog)
    assert not frame_blocked(dialog, "datasheet")
    qtbot.waitUntil(lambda: dialog._install_btn.isEnabled(), timeout=30000)


def test_the_reason_strip_escapes_a_model_name_holding_markup(qtbot, atomic_custom, tmp_path):
    evil = atomic("model_3d", '3D model "<b>x</b>.step" is not in Custom/3DModels (names are case-sensitive)')
    dialog = open_dialog(
        qtbot, atomic_custom, tmp_path, package_members(), core=core_with(build_plan=with_issues(evil))
    )

    assert "<b>x</b>" not in dialog._strip.text()
    assert "&lt;b&gt;x&lt;/b&gt;" in dialog._strip.text()
    assert any("<b>x</b>" in text for text in strip_links(dialog))
    assert html.escape("<b>x</b>") in dialog._strip.toolTip()
