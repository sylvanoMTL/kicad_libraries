#!/usr/bin/env python3
"""One-shot checker for the Abracon ATXK-H14 IPC-7351 rotation in the Custom submodule.

Usage:
    ./env/Scripts/python.exe <this file> [footprint|symbol|all]

Runs kicad-cli (fp/sym upgrade, output ONLY to a temp dir, never in place) and
asserts, on the source files and on KiCad's re-emitted text: the IPC-7351 pad layout
(pin 1 top-left), that it is a 90-degree clockwise rotation of the 261023-ptg top view
and not a mirror, courtyard, F.Fab body outline, the F.SilkS pin-1 dot and its pad
clearance, text positions, metadata and (source only) file hygiene. The symbol and
cleanup checks are kept as regression. Exit 0 = all OK, 1 = any FAIL, 2 = kicad-cli missing.
"""
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from kicad_lib_manager.kicad_files import (  # noqa: E402
    file_version,
    find_property,
    find_symbols,
    footprint_name,
    load,
    parse_bytes,
)
from kicad_lib_manager.models import Issue  # noqa: E402
from kicad_lib_manager.sexpr import Node, unquote  # noqa: E402

LIB = "Oscillator_TCXO_Abracon"
FP_FILE = REPO_ROOT / "Custom" / "Footprints" / f"{LIB}.pretty" / "ATXK-H14.kicad_mod"
FP_DIR = FP_FILE.parent
SYM_FILE = REPO_ROOT / "Custom" / "Symbols" / f"{LIB}.kicad_sym"
OLD_FP_FILE = FP_DIR / ("ATX" + "-14" + ".kicad_mod")
OLD_NAME = "ATX" + "-14"

FP_DATASHEET = SYM_DATASHEET = "https://abracon.com/datasheets/ATXK-H14.pdf"
FP_TEXT = (
    "Abracon ATXK-H14 TCXO, 4-pad SMD 2.15x1.35x1.1mm, pads 0.85x0.70mm, "
    "pitch 1.45x1.00mm, pin 1 top-left (IPC-7351 orientation)"
)
FP_TAGS = "tcxo oscillator 32.768kHz abracon ATXK-H14"
# 261023-ptg landscape (datasheet top view) centres; PADS must be these rotated 90 deg CW
TOPVIEW_PADS = {"1": (-0.725, 0.5), "2": (0.725, 0.5), "3": (0.725, -0.5), "4": (-0.725, -0.5)}
PADS = {"1": (-0.5, -0.725), "2": (-0.5, 0.725), "3": (0.5, 0.725), "4": (0.5, -0.725)}
PAD_SIZE = (0.7, 0.85)
COURTYARD = ((-1.1, -1.4), (1.1, 1.4))
COURTYARD_WIDTH = 0.05
FAB_SEGMENTS = [
    ((-0.375, -1.075), (0.675, -1.075)),
    ((0.675, -1.075), (0.675, 1.075)),
    ((0.675, 1.075), (-0.675, 1.075)),
    ((-0.675, 1.075), (-0.675, -0.775)),
    ((-0.675, -0.775), (-0.375, -1.075)),
]
FAB_WIDTH = 0.1
SILK_DOT_CENTER = (-1.15, -1.1)
SILK_DOT_RADIUS = 0.1
SILK_PAD_CLEARANCE = 0.15
REF_AT = (0.0, -2.1, 0.0)
VALUE_AT = (0.0, 2.1, 0.0)
FAB_REF_AT = (0.0, 0.0, 90.0)
GRAPHIC_HEADS = ("fp_line", "fp_rect", "fp_circle", "fp_arc", "fp_poly")

SYM_DESCRIPTION = "32.768kHz TCXO, CMOS output, \u00b15ppm -40..+85\u00b0C, 1.5-3.63V, 2.15x1.35mm"
SYM_KEYWORDS = "tcxo oscillator 32.768kHz 32k rtc cmos abracon"
SYM_FP_FILTERS = "ATXK*H14*"
SYM_FOOTPRINT = f"{LIB}:ATXK-H14"
PINS = {"1": "OE", "2": "GND", "3": "OUT", "4": "VDD"}

TOL = 1e-6
failures = 0


def ok(msg: str) -> None:
    print(f"OK {msg}")


def fail(msg: str) -> None:
    global failures
    failures += 1
    print(f"FAIL {msg}")


def expect(tag: str, what: str, expected, got) -> None:
    if expected != got:
        fail(f"{tag}: {what} expected {expected!r} got {got!r}")


def find_kicad_cli() -> str | None:
    env = os.environ.get("KICAD_CLI")
    if env and Path(env).is_file():
        return env
    default = Path("C:/Program Files/KiCad/10.0/bin/kicad-cli.exe")
    if default.is_file():
        return str(default)
    return shutil.which("kicad-cli")


def run_cli(cli: str, args: list[str], tag: str) -> bool:
    try:
        r = subprocess.run([cli, *args], capture_output=True, text=True, timeout=120, shell=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        fail(f"{tag}: kicad-cli did not run: {e}")
        return False
    if r.returncode != 0:
        fail(f"{tag}: kicad-cli exit {r.returncode}: {r.stderr.strip() or r.stdout.strip()}")
        return False
    return True


def tokens(node: Node, head: str) -> list[Node]:
    return [c for c in node.children if c.head == head]


def walk(node: Node):
    yield node
    for c in node.children:
        yield from walk(c)


def hygiene(tag: str, loaded, version: int) -> None:
    expect(tag, "version", version, file_version(loaded.root))
    expect(tag, "mixed_eol", False, loaded.source.mixed_eol)
    expect(tag, "bom", False, loaded.source.bom)


def _num(node: Node, idx: int, default: float = 0.0) -> float:
    return float(node.children[idx].text) if len(node.children) > idx else default


def _layer(node: Node) -> str | None:
    ls = tokens(node, "layer")
    return unquote(ls[0].children[1].text) if ls and len(ls[0].children) > 1 else None


def _stroke_width(node: Node) -> float | None:
    for st in tokens(node, "stroke"):
        for w in tokens(st, "width"):
            return _num(w, 1)
    return None


def _close(a, b) -> bool:
    return len(a) == len(b) and all(abs(x - y) <= TOL for x, y in zip(a, b))


def _round_pt(x: float, y: float) -> tuple[float, float]:
    return (round(x, 4) + 0.0, round(y, 4) + 0.0)


def _rect_clearance(p: tuple[float, float], center, size) -> float:
    dx = max(abs(p[0] - center[0]) - size[0] / 2, 0.0)
    dy = max(abs(p[1] - center[1]) - size[1] / 2, 0.0)
    return math.hypot(dx, dy)


def check_graphics(tag: str, fp: Node, pads: dict, sizes: dict) -> None:
    by_layer: dict[str | None, list[Node]] = {}
    for c in fp.children:
        if c.head in GRAPHIC_HEADS:
            by_layer.setdefault(_layer(c), []).append(c)
    # F.CrtYd: exactly one fp_rect
    crt = by_layer.get("F.CrtYd", [])
    if len(crt) != 1 or crt[0].head != "fp_rect":
        fail(f"{tag}: F.CrtYd expected exactly one fp_rect got {[c.head for c in crt]}")
    else:
        r = crt[0]
        st, en = tokens(r, "start")[0], tokens(r, "end")[0]
        x0, x1 = sorted((_num(st, 1), _num(en, 1)))
        y0, y1 = sorted((_num(st, 2), _num(en, 2)))
        got = ((x0, y0), (x1, y1))
        if not (_close(got[0], COURTYARD[0]) and _close(got[1], COURTYARD[1])):
            fail(f"{tag}: courtyard expected {COURTYARD} got {got}")
        w = _stroke_width(r)
        if w is None or abs(w - COURTYARD_WIDTH) > TOL:
            fail(f"{tag}: courtyard stroke width expected {COURTYARD_WIDTH} got {w}")
    # F.Fab: exactly five fp_line, compared as an unordered set of unordered endpoint pairs
    fab = by_layer.get("F.Fab", [])
    if len(fab) != 5 or any(c.head != "fp_line" for c in fab):
        fail(f"{tag}: F.Fab expected exactly five fp_line got {[c.head for c in fab]}")
    else:
        got = set()
        for c in fab:
            st, en = tokens(c, "start")[0], tokens(c, "end")[0]
            got.add(frozenset((_round_pt(_num(st, 1), _num(st, 2)), _round_pt(_num(en, 1), _num(en, 2)))))
            w = _stroke_width(c)
            if w is None or abs(w - FAB_WIDTH) > TOL:
                fail(f"{tag}: F.Fab line stroke width expected {FAB_WIDTH} got {w}")
        want = {frozenset((_round_pt(*a), _round_pt(*b))) for a, b in FAB_SEGMENTS}
        if got != want:
            fail(f"{tag}: F.Fab segments mismatch; missing {sorted(map(sorted, want - got))} extra {sorted(map(sorted, got - want))}")
    # F.SilkS: exactly one filled dot
    silk = by_layer.get("F.SilkS", [])
    if len(silk) != 1 or silk[0].head != "fp_circle":
        fail(f"{tag}: F.SilkS expected exactly one fp_circle got {[c.head for c in silk]}")
    else:
        c = silk[0]
        fills = tokens(c, "fill")
        fill = fills[0].children[1].text if fills and len(fills[0].children) > 1 else None
        if fill not in ("yes", "solid"):
            fail(f"{tag}: silk dot fill expected yes/solid got {fill!r}")
        ce, en = tokens(c, "center")[0], tokens(c, "end")[0]
        center = (_num(ce, 1), _num(ce, 2))
        radius = math.hypot(_num(en, 1) - center[0], _num(en, 2) - center[1])
        if not _close(center, SILK_DOT_CENTER):
            fail(f"{tag}: silk dot centre expected {SILK_DOT_CENTER} got {center}")
        if abs(radius - SILK_DOT_RADIUS) > TOL:
            fail(f"{tag}: silk dot radius expected {SILK_DOT_RADIUS} got {radius}")
        width = _stroke_width(c) or 0.0
        outer = radius + width / 2
        clear = {n: _rect_clearance(center, pads[n], sizes[n]) - outer for n in pads if n in sizes}
        if clear:
            nearest = min(clear, key=clear.get)
            expect(tag, "silk dot nearest pad", "1", nearest)
            if clear[nearest] < SILK_PAD_CLEARANCE - TOL:
                fail(f"{tag}: silk dot clearance {clear[nearest]:.4f} < {SILK_PAD_CLEARANCE}")
            cy = COURTYARD
            over_x = max(cy[0][0] - (center[0] - outer), 0.0)
            print(f"INFO {tag}: silk dot clearance to pad {nearest} {clear[nearest]:.3f} mm; "
                  f"bbox x {center[0]-outer:.3f}..{center[0]+outer:.3f} y {center[1]-outer:.3f}..{center[1]+outer:.3f} "
                  f"vs courtyard {cy}; X overhang {over_x:.3f} mm")


def check_texts(tag: str, fp: Node) -> None:
    def at_of(node: Node):
        a = tokens(node, "at")
        return (_num(a[0], 1), _num(a[0], 2), _num(a[0], 3)) if a else None

    for name, want, layer in (("Reference", REF_AT, "F.SilkS"), ("Value", VALUE_AT, "F.Fab")):
        p = find_property(fp, name)
        if p is None:
            fail(f"{tag}: property {name} missing")
            continue
        got = at_of(p.node)
        if got is None or not _close(got, want):
            fail(f"{tag}: {name} at expected {want} got {got}")
        expect(tag, f"{name} layer", layer, _layer(p.node))
    refs = [
        c for c in tokens(fp, "fp_text")
        if len(c.children) > 2 and c.children[1].text == "user" and unquote(c.children[2].text) == "${REFERENCE}"
    ]
    if len(refs) != 1:
        fail(f"{tag}: expected exactly one ${{REFERENCE}} fp_text user, got {len(refs)}")
    else:
        got = at_of(refs[0])
        if got is None or not _close(got, FAB_REF_AT):
            fail(f"{tag}: ${{REFERENCE}} at expected {FAB_REF_AT} got {got}")
        expect(tag, "${REFERENCE} layer", "F.Fab", _layer(refs[0]))


def check_footprint(tag: str, loaded, source: bool) -> None:
    ref = footprint_name(loaded.root)
    if ref is None:
        fail(f"{tag}: no footprint node")
        return
    fp = ref.node
    expect(tag, "footprint name", "ATXK-H14", ref.name)
    pads = {}
    sizes = {}
    for pad in tokens(fp, "pad"):
        num = unquote(pad.children[1].text)
        kinds = (pad.children[2].text, pad.children[3].text)
        expect(tag, f"pad {num} type/shape", ("smd", "rect"), kinds)
        at = tokens(pad, "at")
        size = tokens(pad, "size")
        if not at or not size:
            fail(f"{tag}: pad {num} missing at/size")
            continue
        pos = (float(at[0].children[1].text), float(at[0].children[2].text))
        rot = _num(at[0], 3)
        sz = (float(size[0].children[1].text), float(size[0].children[2].text))
        pads[num] = pos
        sizes[num] = sz
        if abs(rot) > TOL:
            fail(f"{tag}: pad {num} has rotation {rot}")
        if num in PADS and any(abs(a - b) > TOL for a, b in zip(pos, PADS[num])):
            fail(f"{tag}: pad {num} at expected {PADS[num]} got {pos}")
        if any(abs(a - b) > TOL for a, b in zip(sz, PAD_SIZE)):
            fail(f"{tag}: pad {num} size expected {PAD_SIZE} got {sz}")
    expect(tag, "pad numbers", sorted(PADS), sorted(pads))
    if sorted(pads) == sorted(PADS):
        # rotation, not mirror: (x, y) -> (-y, x) of the top view, same winding sign
        for n, (x, y) in TOPVIEW_PADS.items():
            if not _close(PADS[n], (-y, x)):
                fail(f"{tag}: constants: PADS[{n}] is not the 90 deg CW rotation of TOPVIEW_PADS")
            if not _close(pads[n], (-y, x)):
                fail(f"{tag}: pad {n} is not the 90 deg CW rotation (-y,x)={(-y, x)} of the top view, got {pads[n]}")

        def winding(d: dict) -> float:
            p1, p2, p3 = d["1"], d["2"], d["3"]
            return (p2[0] - p1[0]) * (p3[1] - p2[1]) - (p2[1] - p1[1]) * (p3[0] - p2[0])

        w_new, w_top = winding(pads), winding(TOPVIEW_PADS)
        if not (w_new < 0 and w_top < 0):
            fail(f"{tag}: winding sign 1->2->3 must be negative like the top view (new {w_new}, top {w_top}); mirror?")
        min_x = min(p[0] for p in pads.values())
        min_y = min(p[1] for p in pads.values())
        if abs(pads["1"][0] - min_x) > TOL or abs(pads["1"][1] - min_y) > TOL:
            fail(f"{tag}: pad 1 is not top-left (min x and min y), got {pads['1']}")
        check_graphics(tag, fp, pads, sizes)
    check_texts(tag, fp)
    expect(tag, "model nodes", 0, len(tokens(fp, "model")))
    for name, want in (("Datasheet", FP_DATASHEET), ("Description", FP_TEXT), ("Value", "ATXK-H14")):
        p = find_property(fp, name)
        expect(tag, f"property {name}", want, p.value if p else None)
    for head, want in (("descr", FP_TEXT), ("tags", FP_TAGS)):
        nodes = tokens(fp, head)
        got = unquote(nodes[0].children[1].text) if nodes and len(nodes[0].children) > 1 else None
        expect(tag, head, want, got)
    if source:
        hygiene(tag, loaded, 20241229)


def check_symbol(tag: str, loaded, source: bool) -> None:
    syms = find_symbols(loaded.root)
    expect(tag, "symbol names", ["ATXK-H14"], [s.name for s in syms])
    if len(syms) != 1:
        return
    node = syms[0].node
    want = {
        "Reference": "Y",
        "Value": "ATXK-H14",
        "Footprint": SYM_FOOTPRINT,
        "Datasheet": SYM_DATASHEET,
        "Description": SYM_DESCRIPTION,
        "ki_keywords": SYM_KEYWORDS,
        "ki_fp_filters": SYM_FP_FILTERS,
        "Manufacturer": "Abracon",
    }
    for name, value in want.items():
        p = find_property(node, name)
        expect(tag, f"property {name}", value, p.value if p else None)
    man = find_property(node, "Manufacturer")
    if man is not None:
        hidden = any(
            n.head == "hide" and len(n.children) > 1 and n.children[1].text == "yes" for n in walk(man.node)
        )
        expect(tag, "Manufacturer hidden", True, hidden)
    pins = {}
    for n in walk(node):
        if n.head == "pin":
            name_nodes, num_nodes = tokens(n, "name"), tokens(n, "number")
            if name_nodes and num_nodes:
                pins[unquote(num_nodes[0].children[1].text)] = unquote(name_nodes[0].children[1].text)
    expect(tag, "pin map", PINS, pins)
    if source:
        hygiene(tag, loaded, 20241209)


def load_source(path: Path, tag: str):
    loaded = load(path)
    if isinstance(loaded, Issue):
        fail(f"{tag}: could not load {path.name}: {loaded}")
        return None
    return loaded


def load_bytes(path: Path, tag: str):
    if not path.is_file():
        fail(f"{tag}: kicad-cli output missing: {path}")
        return None
    loaded = parse_bytes(path.read_bytes(), path.name)
    if isinstance(loaded, Issue):
        fail(f"{tag}: could not parse re-emitted {path.name}: {loaded}")
        return None
    return loaded


def check_cleanup(reemit_dir: Path | None) -> None:
    tag = "cleanup/source"
    if OLD_FP_FILE.exists():
        fail(f"{tag}: {OLD_FP_FILE.name} still exists")
    if reemit_dir is not None:
        files = sorted(p.name for p in reemit_dir.iterdir()) if reemit_dir.is_dir() else []
        expect("cleanup/kicad-cli", "re-emitted .pretty files", ["ATXK-H14.kicad_mod"], files)
    needle = OLD_NAME.encode()
    hits = []
    for p in (REPO_ROOT / "Custom").rglob("*"):
        if ".git" in p.parts or not p.is_file():
            continue
        if p.suffix in (".kicad_sym", ".kicad_mod", ".kicad_sch", ".kicad_pcb") and needle in p.read_bytes():
            hits.append(p.relative_to(REPO_ROOT).as_posix())
    expect(tag, "files mentioning the old family name", [], hits)


def main() -> int:
    part = sys.argv[1] if len(sys.argv) > 1 else "all"
    if part not in ("footprint", "symbol", "all"):
        print("usage: check_atxk_h14.py [footprint|symbol|all]")
        return 2
    cli = find_kicad_cli()
    if cli is None:
        print("FAIL kicad-cli not found (set KICAD_CLI or install KiCad 10)")
        return 2
    do_fp = part in ("footprint", "all")
    do_sym = part in ("symbol", "all")
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        reemit_pretty = tmpdir / f"{LIB}.pretty"
        reemit_sym = tmpdir / f"{LIB}.kicad_sym"
        pretty_ok = sym_ok = False
        if do_fp:
            pretty_ok = run_cli(cli, ["fp", "upgrade", "--force", "-o", str(reemit_pretty), str(FP_DIR)], "footprint/kicad-cli")
        if do_sym:
            sym_ok = run_cli(cli, ["sym", "upgrade", "--force", "-o", str(reemit_sym), str(SYM_FILE)], "symbol/kicad-cli")
        if do_fp:
            src = load_source(FP_FILE, "footprint/source")
            if src is not None:
                n = failures
                check_footprint("footprint/source", src, True)
                if failures == n:
                    ok("footprint/source")
            if pretty_ok:
                out = load_bytes(reemit_pretty / "ATXK-H14.kicad_mod", "footprint/kicad-cli")
                if out is not None:
                    n = failures
                    check_footprint("footprint/kicad-cli", out, False)
                    if failures == n:
                        ok("footprint/kicad-cli")
        if do_sym:
            src = load_source(SYM_FILE, "symbol/source")
            if src is not None:
                n = failures
                check_symbol("symbol/source", src, True)
                if failures == n:
                    ok("symbol/source")
            if sym_ok:
                out = load_bytes(reemit_sym, "symbol/kicad-cli")
                if out is not None:
                    n = failures
                    check_symbol("symbol/kicad-cli", out, False)
                    if failures == n:
                        ok("symbol/kicad-cli")
        if part == "all":
            n = failures
            check_cleanup(reemit_pretty if pretty_ok else None)
            if failures == n:
                ok("cleanup")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
