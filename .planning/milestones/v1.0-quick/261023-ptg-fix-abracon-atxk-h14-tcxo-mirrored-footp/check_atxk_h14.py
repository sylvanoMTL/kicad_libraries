#!/usr/bin/env python3
"""One-shot checker for the Abracon ATXK-H14 TCXO fix in the Custom submodule.

Usage:
    ./env/Scripts/python.exe <this file> [footprint|symbol|all]

Runs kicad-cli (fp/sym upgrade, output ONLY to a temp dir, never in place) and
asserts pads, properties, pins, cleanup and file hygiene on the source files and
on KiCad's re-emitted text. Exit 0 = all OK, 1 = any FAIL, 2 = kicad-cli missing.
"""
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
    "pitch 1.45x1.00mm, pin 1 bottom-left (top view)"
)
FP_TAGS = "tcxo oscillator 32.768kHz abracon ATXK-H14"
PADS = {"1": (-0.725, 0.5), "2": (0.725, 0.5), "3": (0.725, -0.5), "4": (-0.725, -0.5)}
PAD_SIZE = (0.85, 0.7)

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


def check_footprint(tag: str, loaded, source: bool) -> None:
    ref = footprint_name(loaded.root)
    if ref is None:
        fail(f"{tag}: no footprint node")
        return
    fp = ref.node
    expect(tag, "footprint name", "ATXK-H14", ref.name)
    pads = {}
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
        sz = (float(size[0].children[1].text), float(size[0].children[2].text))
        pads[num] = pos
        if num in PADS and any(abs(a - b) > TOL for a, b in zip(pos, PADS[num])):
            fail(f"{tag}: pad {num} at expected {PADS[num]} got {pos}")
        if any(abs(a - b) > TOL for a, b in zip(sz, PAD_SIZE)):
            fail(f"{tag}: pad {num} size expected {PAD_SIZE} got {sz}")
    expect(tag, "pad numbers", sorted(PADS), sorted(pads))
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
