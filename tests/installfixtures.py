"""Byte builders for the Phase 4 install tests (INST-02, INST-05, INST-06, POST-04).

This is a plain helper module, not a test module: it has no ``test_`` prefix, so
pytest does not collect it. Test modules import it with ``from installfixtures
import ...``, like ``zipfixtures``. The rule: builders return bytes, write nothing,
take no paths, and import only the standard library and ``zipfixtures._quote``.
"""

from zipfixtures import _quote  # noqa: F401  (used once the builders are filled in)


def target_lib(
    version: int,
    names: tuple[str, ...] = ("EXISTING_A", "EXISTING_B"),
    *,
    eol: str | None = None,
) -> bytes:
    """Build a Custom/ target .kicad_sym in the house style of the given format version."""
    return b""
