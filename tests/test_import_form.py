"""Qt-free left-pane rules of the import dialog (plan 05-07): item choices and field text become InstallOptions."""

from kicad_lib_manager.importer.form import FIELD_NAMES, FieldDefaults, FormValues, build_options
from kicad_lib_manager.importer.plan import Resolution

DEFAULTS = FieldDefaults(
    value="PART",
    datasheet="https://example.com/part",
    description="",
    manufacturer="TI",
    mpn="PART",
)


def values(**changes) -> FormValues:
    base = {
        "library": "Lib",
        "symbol": None,
        "footprints": (),
        "model": None,
        "no_model": False,
        "footprint_name": None,
        "fields": {},
        "resolutions": {},
    }
    base.update(changes)
    return FormValues(**base)


def test_field_names_are_the_five_planner_overrides():
    assert FIELD_NAMES == ("value", "datasheet", "description", "manufacturer", "mpn")


def test_build_options_items():
    options = build_options(
        FormValues(
            library=" Lib ",
            symbol="S2",
            footprints=("F2", "F1"),
            model=None,
            no_model=True,
            footprint_name=None,
            fields={},
            resolutions={},
        ),
        DEFAULTS,
    )
    assert options.library == "Lib"
    assert options.symbol == "S2"
    assert options.footprints == ("F2", "F1")
    assert options.no_model is True
    assert options.model is None
    assert dict(options.footprint_names) == {}
    assert options.cleared == frozenset()
    assert [getattr(options, name) for name in FIELD_NAMES] == [None] * 5


def test_build_options_copies_resolutions():
    chosen = {"footprint:F1": Resolution("skip")}
    options = build_options(values(resolutions=chosen), DEFAULTS)
    assert dict(options.resolutions) == chosen
    assert options.resolutions is not chosen
