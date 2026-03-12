import re
import shutil
from pathlib import Path

from .models import FootprintLibrary, SymbolLibrary

ENV_VAR = "KICAD_LIB_GITHUB"


def generate_sym_lib_table(libs: list[SymbolLibrary]) -> str:
    selected = [lib for lib in libs if lib.selected]
    lines = ["(sym_lib_table"]
    for lib in selected:
        lines.append(
            f'  (lib (name "{lib.nickname}")(type "KiCad")'
            f'(uri "${{{ENV_VAR}}}/{lib.rel_path}")'
            f'(options "")(descr ""))'
        )
    lines.append(")")
    return "\n".join(lines) + "\n"


def generate_fp_lib_table(libs: list[FootprintLibrary]) -> str:
    selected = [lib for lib in libs if lib.selected]
    lines = ["(fp_lib_table"]
    for lib in selected:
        lines.append(
            f'  (lib (name "{lib.nickname}")(type "KiCad")'
            f'(uri "${{{ENV_VAR}}}/{lib.rel_path}")'
            f'(options "")(descr ""))'
        )
    lines.append(")")
    return "\n".join(lines) + "\n"


def backup_existing(file_path: Path) -> Path | None:
    if not file_path.exists():
        return None

    base_name = file_path.name
    parent = file_path.parent
    max_num = 0
    pattern = re.compile(re.escape(base_name) + r"_backup_(\d+)$")

    for f in parent.iterdir():
        m = pattern.match(f.name)
        if m:
            max_num = max(max_num, int(m.group(1)))

    backup_name = f"{base_name}_backup_{max_num + 1}"
    backup_path = parent / backup_name
    shutil.copy2(file_path, backup_path)
    return backup_path


def write_tables(dest_folder: Path,
                 sym_libs: list[SymbolLibrary],
                 fp_libs: list[FootprintLibrary]) -> list[str]:
    messages = []
    dest_folder.mkdir(parents=True, exist_ok=True)

    sym_path = dest_folder / "sym-lib-table"
    fp_path = dest_folder / "fp-lib-table"

    for path, content, label in [
        (sym_path, generate_sym_lib_table(sym_libs), "sym-lib-table"),
        (fp_path, generate_fp_lib_table(fp_libs), "fp-lib-table"),
    ]:
        backup = backup_existing(path)
        if backup:
            messages.append(f"Backed up {label} -> {backup.name}")
        path.write_text(content, encoding="utf-8")
        messages.append(f"Written {label} to {path}")

    return messages


def list_backups(folder: Path) -> list[Path]:
    backups = []
    pattern = re.compile(r"(sym-lib-table|fp-lib-table)_backup_\d+$")
    if folder.exists():
        for f in sorted(folder.iterdir()):
            if f.is_file() and pattern.match(f.name):
                backups.append(f)
    return backups


def restore_backup(backup_path: Path) -> list[str]:
    messages = []
    name = backup_path.name
    # Extract base name: remove _backup_N suffix
    base_name = re.sub(r"_backup_\d+$", "", name)
    current_path = backup_path.parent / base_name

    # Back up current file before restoring
    backup = backup_existing(current_path)
    if backup:
        messages.append(f"Backed up current {base_name} -> {backup.name}")

    shutil.copy2(backup_path, current_path)
    messages.append(f"Restored {name} -> {base_name}")
    return messages
