#!/usr/bin/env python3
"""
Generate KiCad sym-lib-table and fp-lib-table files for all libraries
found in this repository.

Usage:
    python generate_lib_tables.py

This scans for .kicad_sym files and .pretty directories, then generates
library table files using the ${KICAD_LIB_GITHUB} environment variable
so paths remain portable across machines.

Setup in KiCad:
    1. Go to Preferences > Configure Paths
    2. Add: KICAD_LIB_GITHUB = <path to this repo>
       e.g. C:\Git_Repo_Clones\Kicad_Libraries
    3. Copy the generated table entries into your global library tables:
       - Preferences > Manage Symbol Libraries > paste sym-lib-table entries
       - Preferences > Manage Footprint Libraries > paste fp-lib-table entries
       Or replace the files directly (see output paths below).
"""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).parent.resolve()
ENV_VAR = "KICAD_LIB_GITHUB"


def find_symbol_libs(root: Path) -> list[tuple[str, str]]:
    """Return list of (nickname, relative_path) for all .kicad_sym files."""
    libs = []
    for f in sorted(root.rglob("*.kicad_sym")):
        rel = f.relative_to(root).as_posix()
        nickname = f.stem
        libs.append((nickname, rel))
    return libs


def find_footprint_libs(root: Path) -> list[tuple[str, str]]:
    """Return list of (nickname, relative_path) for all .pretty directories."""
    libs = []
    for d in sorted(root.rglob("*.pretty")):
        if d.is_dir():
            rel = d.relative_to(root).as_posix()
            nickname = d.stem
            libs.append((nickname, rel))
    return libs


def generate_sym_lib_table(libs: list[tuple[str, str]]) -> str:
    lines = ["(sym_lib_table"]
    for nickname, rel_path in libs:
        lines.append(
            f'  (lib (name "{nickname}")(type "KiCad")'
            f'(uri "${{{ENV_VAR}}}/{rel_path}")'
            f'(options "")(descr ""))'
        )
    lines.append(")")
    return "\n".join(lines) + "\n"


def generate_fp_lib_table(libs: list[tuple[str, str]]) -> str:
    lines = ["(fp_lib_table"]
    for nickname, rel_path in libs:
        lines.append(
            f'  (lib (name "{nickname}")(type "KiCad")'
            f'(uri "${{{ENV_VAR}}}/{rel_path}")'
            f'(options "")(descr ""))'
        )
    lines.append(")")
    return "\n".join(lines) + "\n"


def main():
    sym_libs = find_symbol_libs(REPO_ROOT)
    fp_libs = find_footprint_libs(REPO_ROOT)

    sym_table = generate_sym_lib_table(sym_libs)
    fp_table = generate_fp_lib_table(fp_libs)

    sym_out = REPO_ROOT / "sym-lib-table"
    fp_out = REPO_ROOT / "fp-lib-table"

    sym_out.write_text(sym_table, encoding="utf-8")
    fp_out.write_text(fp_table, encoding="utf-8")

    print(f"Found {len(sym_libs)} symbol libraries, {len(fp_libs)} footprint libraries.")
    print(f"Written: {sym_out}")
    print(f"Written: {fp_out}")
    print()
    print("Next steps:")
    print(f"  1. In KiCad: Preferences > Configure Paths")
    print(f"     Add: {ENV_VAR} = {REPO_ROOT}")
    print(f"  2. Copy the contents of sym-lib-table and fp-lib-table")
    print(f"     into your KiCad global library tables, or replace them directly at:")
    print(f"     - Windows: %APPDATA%/kicad/<version>/sym-lib-table")
    print(f"     - Windows: %APPDATA%/kicad/<version>/fp-lib-table")


if __name__ == "__main__":
    main()
