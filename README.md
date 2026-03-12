# KiCad Libraries

Central repository that aggregates all KiCad libraries (open-source and custom) using git submodules.

## Repository Structure

```
Kicad_Libraries/
├── Custom/                       ← Personal parts (submodule: kicad_custom_library)
│   ├── Symbols/
│   └── Footprints/
├── WurthElektronik/
│   └── KiCad-Library/            ← Wurth open-source library (submodule)
├── generate_lib_tables.py        ← Script to generate KiCad library tables
├── sym-lib-table                 ← Generated symbol library table
└── fp-lib-table                  ← Generated footprint library table
```

## Setup

### 1. Clone the repository

```bash
git clone --recurse-submodules https://github.com/sylvanoMTL/kicad_libraries.git
```

If you already cloned without `--recurse-submodules`:

```bash
git submodule update --init --recursive
```

### 2. Generate library tables

```bash
python generate_lib_tables.py
```

This scans the repo for all `.kicad_sym` files and `.pretty` directories and generates `sym-lib-table` and `fp-lib-table` using the `${KICAD_LIBS_GITHUB}` environment variable for portable paths.

### 3. Configure KiCad

1. Open KiCad
2. Go to **Preferences > Configure Paths**
3. Add a new entry:
   - **Name:** `KICAD_LIBS_GITHUB`
   - **Path:** `<path to this repo>` (e.g., `C:\Git_Repo_Clones\Kicad_Libraries`)
4. Import the library tables using one of these methods:

#### Option A: Replace global tables

Copy the generated files to your KiCad config directory:

- **Windows:** `%APPDATA%\kicad\<version>\`
- **Linux:** `~/.config/kicad/<version>/`
- **macOS:** `~/Library/Preferences/kicad/<version>/`

> **Note:** Back up your existing `sym-lib-table` and `fp-lib-table` first if you have other libraries configured.

#### Option B: Append to existing tables

1. Go to **Preferences > Manage Symbol Libraries**
2. Click the folder icon to import, and select the generated `sym-lib-table`
3. Repeat for **Preferences > Manage Footprint Libraries** with `fp-lib-table`

## Adding a new open-source library

```bash
git submodule add <repo-url> <VendorName>/<LibName>
python generate_lib_tables.py
```

Then re-import the updated tables into KiCad.

## Updating submodules

Pull the latest changes from all upstream libraries:

```bash
git submodule update --remote --merge
```
