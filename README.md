# PDF Processing Toolkit

![Python](https://img.shields.io/badge/python-3.10+-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)
![Required Dependencies](https://img.shields.io/badge/dependencies-4_required-orange)
![OCR](https://img.shields.io/badge/OCR-optional-yellowgreen)
![Status](https://img.shields.io/badge/status-active-brightgreen)
![Windows Only](https://img.shields.io/badge/batch__print-Windows_only-informational)
![Code Style](https://img.shields.io/badge/code_style-PEP8-black)

A modular command-line toolkit for processing PDF documents. Run `main.py` to access all features through a central menu.

---

## Table of Contents

- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [How to Run](#how-to-run)
- [Building a Standalone Executable](#building-a-standalone-executable)
- [Modules](#modules)
  - [1. PDF Scanner](#1-pdf-scanner)
  - [2. Brand Reader](#2-brand-reader)
  - [3. Batch Print](#3-batch-print)
  - [4. Configuration Editor](#4-configuration-editor)
- [Adding a New Module](#adding-a-new-module)
- [Troubleshooting](#troubleshooting)
- [Notes](#notes)

---

## Project Structure

```
project/
├── main.py                  ← entry point and main menu
├── config.py                ← centralized settings for all modules
└── modules/
    ├── __init__.py          ← marks modules/ as a Python package (intentionally empty)
    ├── documentManager.py   ← scans a drive and copies matching PDFs
    ├── brandReader.py        ← extracts brand name fields into Excel
    ├── batchPrinter.py       ← batch prints PDFs to a physical printer
    └── configEditor.py       ← interactive configuration settings editor
```

> Module files use the names above, matching the imports in `main.py`
> (`modules.documentManager`, `modules.brandReader`, `modules.batchPrinter`, `modules.configEditor`).

---

## Requirements

### Python
Python 3.10 or higher — required for the `str | None` type hint syntax used throughout the modules.

To check your version:
```
python --version
```

### Python Dependencies

Install all required packages in one command:
```
pip install pypdf pdfplumber openpyxl pywin32
```

| Package    | Required by                     | Purpose                              |
|------------|----------------------------------|---------------------------------------|
| pypdf      | documentManager, brandReader     | Primary PDF text extraction          |
| pdfplumber | documentManager, brandReader     | Fallback extraction for complex layouts |
| openpyxl   | brandReader                      | Writing formatted Excel reports      |
| pywin32    | batchPrinter                     | Windows printer spooler access       |

### Optional — OCR Support

Only required if your PDFs are scanned images rather than digitally created documents. The toolkit functions without OCR — it simply skips the OCR step.

```
pip install pytesseract pdf2image
```

You must also install the following external binaries:

**Tesseract OCR**
Download: https://github.com/UB-Mannheim/tesseract/wiki
Default path expected: `C:\Program Files\Tesseract-OCR\tesseract.exe`
Update `TESSERACT_PATH` in `config.py` if installed elsewhere.

**Poppler**
Download: https://github.com/oschwartz10612/poppler-windows/releases
Default path expected: `C:\poppler-26.02.0\Library\bin`
Update `POPPLER_PATH` in `config.py` if installed elsewhere.

### Required for Batch Printing — Ghostscript

The Batch Print module uses Ghostscript to send PDFs to the printer, forcing
a consistent paper size regardless of the source PDF's page size.

Download: https://www.ghostscript.com/releases/gsdnld.html (Windows 64-bit installer)

Default path expected: `C:\Program Files\gs\<version>\bin\gswin64c.exe`
Update `GHOSTSCRIPT_PATH` in `config.py` to match your installed version —
the version folder name (e.g. `gs10.07.1`) changes with each release, so
this must be updated after every Ghostscript upgrade.

> **Licensing note:** Ghostscript is distributed under AGPL or a commercial
> license. Calling the unmodified `gswin64c.exe` binary via subprocess for
> internal batch printing is generally considered low-risk under AGPL
> (no modification or network-service redistribution involved), but if your
> organization has a formal software compliance process, confirm this usage
> against it before deploying.

---

## Installation

1. Clone or download this repository into a local folder.

2. Install Python dependencies:
   ```
   pip install pypdf pdfplumber openpyxl pywin32
   ```

3. If OCR is needed:
   ```
   pip install pytesseract pdf2image
   ```
    Then install Tesseract and Poppler binaries (see links above) and update
    `TESSERACT_PATH` / `POPPLER_PATH` in `config.py` (or use the interactive
    Configuration Editor in `main.py` to set them).

4. For batch printing, install Ghostscript:
   Download from https://www.ghostscript.com/releases/gsdnld.html and update
   `GHOSTSCRIPT_PATH` in `config.py` to match the installed `gswin64c.exe` path
   (or set it via the Configuration Editor).

5. Set `PRINTER_NAME` in `config.py` to the exact printer name as registered
   in Windows (Settings → Bluetooth & devices → Printers & scanners). This can
   also be adjusted via the Configuration Editor. This is checked automatically
   at the start of every batch print run — see [Batch Print](#3-batch-print) below.

6. Run the toolkit:
   ```
   python main.py
   ```

---

## How to Run

From inside the `project/` folder:
```
python main.py
```

You will be presented with the following menu:
```
=======================================================
  PDF Processing Toolkit
=======================================================
  1. Scan drive and copy matching PDFs       (pdf_scanner)
  2. Extract brand names to Excel            (brand_reader)
  3. Batch print PDFs to printer             (batch_print)
  4. Configure Toolkit Settings              (config_editor)
  0. Exit
=======================================================
```

Select an option by typing the number and pressing Enter. After each
operation completes, press Enter to return to the menu.

If a module's dependencies are missing, its menu entry is marked
`⚠ missing deps` and selecting it prints the required `pip install` command
instead of running.

---

## Building a Standalone Executable

For deployment to machines that shouldn't need Python, pip, or any of the
external OCR/print tools manually installed, the toolkit can be packaged
into a self-contained folder via PyInstaller. The end result runs with a
double-click — no dependencies, no setup, on any Windows machine.

> This packages the **whole toolkit as one unit**. There is no per-module
> packaging — `main.py` and all four feature modules are bundled together.

### What Gets Bundled

| Layer                         | How it's included                                                  |
|--------------------------------|----------------------------------------------------------------------|
| Python interpreter + this codebase | Bundled automatically by PyInstaller                          |
| pip dependencies (pypdf, pdfplumber, openpyxl, pywin32, pytesseract, pdf2image) | Bundled automatically by PyInstaller |
| Tesseract, Poppler, Ghostscript | **Not** picked up automatically — these are external programs, not Python packages. Must be manually copied into `vendor/` (see below) before building |

### 1. Populate `vendor/`

Create this structure at the project root, copying from wherever you
already have each tool installed (or a fresh download):

```
vendor/
├── tesseract/          ← entire Tesseract-OCR install folder
│   ├── tesseract.exe
│   ├── tessdata/       ← must include at least eng.traineddata
│   └── *.dll
├── poppler/
│   └── bin/            ← entire Library\bin folder (pdftoppm.exe + its DLLs)
└── ghostscript/        ← entire gs<version> install folder
    ├── bin/            ← gswin64c.exe + gsdll64.dll (the exe alone will not run without this DLL)
    ├── lib/
    └── Resource/
```

Copy the **whole** install folder for each tool, not just the single
`.exe` — each depends on sibling DLLs, data files, or resource folders to
function:

```
robocopy "C:\Program Files\Tesseract-OCR"        vendor\tesseract   /E
robocopy "C:\poppler-26.02.0\Library\bin"         vendor\poppler\bin /E
robocopy "C:\Program Files\gs\gs10.07.1"          vendor\ghostscript /E
```

Adjust the source paths above to wherever these are actually installed on
your machine — confirm with `dir` before copying rather than assuming the
`config.py` defaults match your install.

`vendor/` is excluded from git (see `.gitignore`) — it's fetched/copied
fresh per machine that builds the exe, not tracked as source.

### 2. How Path Resolution Works

`config.py` resolves `TESSERACT_PATH`, `POPPLER_PATH`, and
`GHOSTSCRIPT_PATH` relative to a `BASE_DIR`:

- When running from source (`python main.py`), `BASE_DIR` is the project
  folder, and if `vendor/` isn't present there, the original hardcoded
  `C:\Program Files\...` paths are used as a fallback — so a dev machine
  with these tools already installed the normal way still works
  unmodified.
- When running as the built exe, `BASE_DIR` is the folder the `.exe`
  itself lives in (via `sys.executable`), so it looks for `vendor/`
  sitting next to the `.exe`.

`config_local.json` (written by the Configuration Editor) is also resolved
against this same `BASE_DIR`, so saved settings persist correctly next to
the exe rather than being lost.

> **Do not build with `--onefile`.** A one-file exe extracts everything —
> including where `config_local.json` would be written — into a temporary
> folder that PyInstaller deletes on exit, silently discarding every
> setting saved through the Configuration Editor on each run. The build
> below uses `--onedir`, which keeps a stable, persistent folder instead.

### 3. Build

Requires PyInstaller in addition to the toolkit's normal dependencies:
```
pip install pyinstaller pywin32 pypdf pdfplumber pdf2image pytesseract openpyxl
```

Run `build.bat` from the project root (PowerShell requires the `.\` prefix
to run a script from the current folder: `.\build.bat`). It will:

1. Clean any previous `build/`/`dist/` output
2. Run PyInstaller (`--onedir --console`, with `--collect-submodules
   modules` so the four feature modules — which `main.py` imports
   dynamically by string via `importlib`, not a static `import` statement
   PyInstaller can trace on its own — are actually included)
3. Copy `vendor/` into the built output, so the result needs nothing
   installed on the target machine

Result:
```
dist/PDF-Toolkit/
├── PDF-Toolkit.exe
├── vendor/           ← copied in by build.bat
└── _internal/        ← PyInstaller's bundled Python runtime + dependencies
```

> If `pyinstaller`/`PyInstaller` isn't recognized as a command even after
> installing it, invoke it as a module instead — `build.bat` already does
> this: `python -m PyInstaller ...`. Python's import system is
> case-sensitive even on Windows, so the package must be referenced as
> `PyInstaller`, not `pyinstaller`, when invoked this way.

### 4. Distribute

Copy the **entire** `dist/PDF-Toolkit/` folder as one unit — not just the
`.exe` — to the target machine (zip it for easier transfer). `.exe`,
`vendor/`, and `_internal/` all depend on each other; none of them work
standalone.

Before trusting it, test on the target machine by running from an already
open console (not double-click), so any startup error stays visible
instead of the window closing before you can read it:
```
cd path\to\PDF-Toolkit
.\PDF-Toolkit.exe
```
Then specifically verify:
- The menu appears without error
- A setting changed via the Configuration Editor survives closing and
  reopening the exe
- OCR extraction succeeds against a scanned/image-only PDF (a PDF with a
  text layer will skip OCR entirely and won't actually test Tesseract/Poppler)

Ideally, run this test on a machine that has never had Python, Tesseract,
Poppler, or Ghostscript installed — that's the only way to confirm the
bundling is actually complete rather than being masked by tools already
present on the build machine.

---

## Modules

---

### 1. PDF Scanner (`modules/documentManager.py`)

Recursively walks a drive or folder, identifies PDFs that match a configurable keyword and regex combination, and copies them to a destination folder.

#### Matching Logic

A PDF qualifies only when **both** of the following conditions are true:

1. At least **one keyword** from `KEYWORDS` is found anywhere in the extracted text (case-insensitive), AND
2. At least `MATCH_THRESHOLD` of the `MATCHERS` regex patterns also match

Pages are read one at a time and scanning stops the moment both conditions are satisfied — the remaining pages are never read.

#### Default Keywords (OR logic — any one qualifies)
```
Certificate of Good Manufacturing Practice
Certificate of Product Registration
Certificate of Listing of Identical Drug Product
```

#### Default Regex Patterns (6 total, threshold: 2)
```
Brand Name:
Registration Number:
FDA Registration No.:
Valid Until <date>
Manufacturer:
Importer / Distributor:
```

To add keywords, append to the `KEYWORDS` list in `documentManager.py`.
To make matching stricter, raise `MATCH_THRESHOLD` in `config.py`.

#### Text Extraction Fallback Chain

```
pypdf  →  pdfplumber  →  OCR (Tesseract)
```

- **pypdf** — fastest, works on standard digitally created PDFs
- **pdfplumber** — slower, handles complex layouts, tables, and multi-column text
- **OCR** — slowest, used only when extracted text is below `TEXT_THRESHOLD` characters

If a method returns sufficient text and the match conditions are met, the remaining methods are never attempted.

#### Drive Walk Behavior

- Walks all subdirectories recursively regardless of nesting depth
- Walk and processing run **concurrently** — the first file starts processing while the walker is still discovering new directories
- The destination folder is automatically excluded from the walk to prevent re-processing already-copied files
- Current directory being scanned is displayed on a single overwriting console line

**Folders always skipped:**
```
.* (any hidden folder)    $* (system folders)    ~* (temp folders)
Windows                   Program Files          Program Files (x86)
ProgramData               System Volume Information    winnt
```

#### Duplicate Handling

Files are SHA-256 hashed before copying:
- Files under 512 KB: full file hashed
- Files over 512 KB: first + last 256 KB hashed (for speed)

If a matching file with identical content has already been copied in the current run (regardless of filename or location), it is skipped and logged under DUPLICATES in the output log.

#### Configuration

All settings are in `config.py`:

| Setting           | Default | Description                                         |
|-------------------|---------|-----------------------------------------------------|
| `SEARCH_ROOT`     | `""`    | Drive or folder to scan. Empty = prompted at runtime |
| `DEST_FOLDER`     | `""`    | Destination for copied files. Empty = prompted      |
| `MAX_WORKERS`     | 4       | Parallel worker processes (bypasses GIL)            |
| `MAX_PAGES`       | 5       | Maximum pages to scan per PDF                       |
| `TEXT_THRESHOLD`  | 50      | Minimum characters before trying next extractor     |
| `FILE_TIMEOUT`    | 30      | Seconds before abandoning a single file             |
| `MIN_FILE_SIZE`   | 1024    | Skip files smaller than this in bytes               |
| `MAX_FILE_SIZE`   | 0       | Skip files larger than this in bytes (0 = no limit) |
| `MOVE_FILES`      | False   | True = move files, False = copy files               |
| `SKIP_DUPLICATES` | True    | Skip files with identical content                   |
| `SKIP_HIDDEN`     | True    | Skip hidden and system folders                      |
| `MATCH_THRESHOLD` | 2       | Minimum regex pattern hits required                 |
| `OCR_DPI`         | 150     | DPI for OCR image rendering                         |
| `TESSERACT_PATH`  | —       | Full path to `tesseract.exe`                        |
| `POPPLER_PATH`    | —       | Full path to Poppler `bin` folder                   |

> **Important:** `MOVE_FILES` defaults to `False`. Always verify results in copy mode before switching to `True`. Moving files is irreversible.

#### Output

A `scan_results.txt` log is written to the destination folder containing:
- Full source → destination path for every copied file
- All skipped files (no match)
- All duplicate files (same content, skipped)
- All errors with error messages
- Summary counts at the bottom

---

### 2. Brand Reader (`modules/brandReader.py`)

Scans all PDFs in a single folder and extracts structured regulatory fields into a formatted Excel report.

#### Fields Extracted

| Field            | Pattern matched                                          |
|------------------|------------------------------------------------------------|
| Brand Name       | `Brand Name:`                                            |
| Registration No. | `Registration Number:` / `FDA Registration No.:`        |
| Valid Until      | `valid until <date>`                                     |
| Manufacturer     | `Manufacturer:` / `Manufacturer Name and Address:`       |
| Trader           | `Trader:`                                                |
| Importer         | `Importer:` / `Importer / Distributor:`                  |
| Distributor      | `Distributor:`                                           |

#### Text Extraction Fallback Chain

Same as the PDF Scanner: pypdf → pdfplumber → OCR (Tesseract).

#### Configuration

All settings are in `config.py`:

| Setting          | Default | Description                                     |
|------------------|---------|-----------------------------------------------------|
| `MAX_WORKERS`    | 4       | Parallel worker threads                         |
| `MAX_PAGES`      | 5       | Maximum pages to scan per PDF                   |
| `OCR_DPI_HIGH`   | 300     | DPI for OCR rendering                           |
| `TEXT_THRESHOLD` | 50      | Minimum characters before trying next extractor |
| `TESSERACT_PATH` | —       | Full path to `tesseract.exe`                    |
| `POPPLER_PATH`   | —       | Full path to Poppler `bin` folder               |

#### Output

A `brand_results.xlsx` file is written to the scanned folder. If the file already exists it is saved as `brand_results(1).xlsx`, `brand_results(2).xlsx`, and so on — existing files are never overwritten.

The Excel report is divided into three labeled sections:

| Section   | Contents                                           |
|-----------|--------------------------------------------------|
| ✔ FOUND   | Files where Brand Name was successfully extracted  |
| ✘ NOT FOUND | Files processed but Brand Name was not found     |
| ⚠ ERRORS  | Files that could not be read or caused exceptions  |

A summary row at the bottom shows total counts for each section.

---

### 3. Batch Print (`modules/batchPrinter.py`)

Sends the first page of all PDFs in a folder to a physical printer in natural sort order, with a live dashboard showing real-time print queue state.

> **Windows only.** This module requires `pywin32` and the Windows print spooler. It will not run on macOS or Linux.

#### How It Works

1. On startup, `_validate_environment()` confirms `GHOSTSCRIPT_PATH` points to
   an existing file and `PRINTER_NAME` matches a printer registered in
   Windows. If either check fails, the run aborts immediately — on a
   printer-name mismatch, the actual list of registered printer names is
   printed so `config.py` can be corrected.
2. PDFs are sorted in natural order (`cert2.pdf` before `cert10.pdf`)
3. Before sending each file, the module checks the spooler — if
   `MAX_ACTIVE_JOBS` is already in the queue, it waits
4. Page 1 of each file is sent via Ghostscript (`mswinpr2` device) in silent
   mode. The job is forced to Letter paper and the page content is scaled to
   fit (`-sPAPERSIZE=letter`, `-dFIXEDMEDIA`, `-dPDFFitPage`), which resolves
   A4/Letter paper-size mismatches when source PDFs are A4-sized but the
   printer tray is loaded with Letter
5. The spooler job ID is captured by comparing job lists before and after
   sending — if Ghostscript completes the job too quickly for the spooler to
   register it, the file is marked complete immediately rather than left
   "in progress" indefinitely
6. Completed jobs are detected when their ID disappears from the active spooler
7. After the last file is sent, a drain loop waits up to `DRAIN_TIMEOUT`
   seconds for all remaining jobs to clear

#### Configuration

All settings are in `config.py`:

| Setting            | Default                | Description                                    |
|--------------------|-------------------------|--------------------------------------------------|
| `PRINTER_NAME`     | `DocuPrint M455 df`     | Exact printer name as registered in Windows — verified automatically at the start of every run |
| `GHOSTSCRIPT_PATH` | —                       | Full path to `gswin64c.exe` (e.g. `C:\Program Files\gs\gs10.07.1\bin\gswin64c.exe`) |
| `MAX_ACTIVE_JOBS`  | 2                       | Maximum concurrent spooler jobs before waiting |

To find the exact printer name: open **Settings → Bluetooth & devices →
Printers & scanners**, click the printer, and copy the name exactly as
displayed. If `PRINTER_NAME` doesn't match, the next run will print the full
list of registered names so you can correct it.

> `SUMATRA_PATH` remains defined in `config.py` for backward compatibility
> but is no longer used by `batchPrinter`.

#### Output

A `print_history.txt` log is written to the PDF source folder on completion, listing all printed files in order. Files that failed to send are tagged with `[FAILED]`.

---

### 4. Configuration Editor (`modules/configEditor.py`)

An interactive, menu-driven CLI configuration editor. It allows you to view, validate, and customize all toolkit settings dynamically without manually editing Python files.

#### Key Features

- **Interactive Menus**: Settings are organized into 5 logical categories (Global/Concurrency, PDF Scanner, Brand Reader, Batch Printer, and OCR Engine).
- **Automatic Validation**: Validates user inputs on the fly (e.g., checks if specified paths exist, verifies non-negative integers, and converts boolean inputs).
- **Persistent Overrides**: Saves configuration overrides to `config_local.json` in the project root. This file is automatically loaded by `config.py` so customized settings persist across runs.
- **In-Memory Session Sync**: Changed settings are synced in-memory dynamically in real-time to already-loaded pipeline modules during the active toolkit session.

#### Configuration Categories

| Category | Description | Key Settings Managed |
|---|---|---|
| **1. Global & Concurrency Settings** | General execution limits. | `MAX_WORKERS`, `MAX_PAGES` |
| **2. PDF Scanner Settings** | PDF scanning paths and thresholds. | `SEARCH_ROOT`, `DEST_FOLDER`, `SCAN_LOG_FILE`, `MATCH_THRESHOLD`, `MOVE_FILES`, `SKIP_DUPLICATES`, `SKIP_HIDDEN`, `MIN_FILE_SIZE`, `MAX_FILE_SIZE`, `FILE_TIMEOUT` |
| **3. Brand Reader Settings** | Brand reader extraction reporting. | `BRAND_LOG_FILE` |
| **4. Batch Printer Settings** | Printer target configuration. | `PRINTER_NAME`, `MAX_ACTIVE_JOBS`, `GHOSTSCRIPT_PATH` |
| **5. OCR Engine Settings** | External binaries and OCR DPI. | `TESSERACT_PATH`, `POPPLER_PATH`, `OCR_DPI`, `OCR_DPI_HIGH`, `TEXT_THRESHOLD` |

---

## Adding a New Module

1. Create `modules/yourModule.py` with a `run()` function:
   ```python
   def run(folder_path: str) -> None:
       # your logic here
   ```

2. In `main.py`, import it with `_try_import` (returns `None` if dependencies are missing, rather than crashing):
   ```python
   your_module = _try_import("modules.yourModule")
   ```

3. Add an entry to `MENU_ENTRIES`:
   ```python
   MENU_ENTRIES = [
       ...
       (
           "Your feature description                (your_module)",
           your_module,
           "launch_your_module",
       ),
   ]
   ```

4. Add a launcher function, including a missing-dependency check:
   ```python
   def launch_your_module():
       if your_module is None:
           _missing_deps_notice("yourModule", "required-package")
           return
       print("\n── Your Module ──────────────────────────────────────")
       folder = prompt_path("Enter folder path", must_exist=True)
       your_module.run(folder)
   ```

Menu numbering updates automatically based on `MENU_ENTRIES`'s order and length.

---

## Troubleshooting

**Menu entry shows `⚠ missing deps`**
The corresponding module's dependencies aren't installed. Selecting the entry prints the required `pip install` command — run it and restart `main.py`.

**`ModuleNotFoundError: No module named 'win32print'`**
Run `pip install pywin32`. This is required for Batch Print only.

**`ModuleNotFoundError: No module named 'pytesseract'`**
OCR is optional. If not installed, the toolkit falls back to text-only extraction. Install with `pip install pytesseract pdf2image` only if your PDFs are scanned images.

**PDF scanner finds no matches**
- Confirm your PDFs contain one of the three certificate title keywords
- Lower `MATCH_THRESHOLD` to `1` in `config.py` temporarily to test keyword-only matching
- If PDFs are scanned images, ensure OCR is installed and `OCR_DPI` is at least 200

**Brand reader returns empty fields**
- The field labels in the PDF must match the regex patterns (e.g. `Brand Name:`, `Manufacturer:`)
- Check if the PDF is image-based — if so, OCR must be installed
- `OCR_DPI_HIGH` (default 300) is used for brand extraction; raise it for low-quality scans

**`❌ Ghostscript not found at: ...`**
Update `GHOSTSCRIPT_PATH` in `config.py` — the version folder name (e.g. `gs10.07.1`) changes with each Ghostscript release, so this needs updating after upgrades.

**`❌ Printer 'X' not found in Windows printer list.`**
`PRINTER_NAME` in `config.py` doesn't exactly match a printer registered in Windows. The error prints the full list of available names — copy the exact string (including any manufacturer prefix) into `PRINTER_NAME`.

**A small window showing a percentage briefly appears for each printed file**
This is the printer driver's own status display during the Ghostscript job. It closes automatically once the job is sent and does not block the batch loop.

**Batch print sends jobs but dashboard shows no completion**
- Verify `PRINTER_NAME` matches exactly (see above)
- Ghostscript jobs may clear from the spooler before `EnumJobs` ever sees them — the dashboard handles this by marking such files complete immediately; check the physical printer for output to confirm

**Printer spooler is unreachable**
`safe_get_jobs()` will retry 3 times with a 5-second delay between attempts before returning an empty job list. If the printer is consistently unreachable, check that the print spooler service is running: `services.msc` → Print Spooler → Started.

**Packaged `.exe` opens and closes immediately**
Run it from an already-open console instead of double-clicking (`cd` into
the folder, then `.\PDF-Toolkit.exe`) so any startup error stays on screen
instead of vanishing when the window closes. A `ModuleNotFoundError: No
module named 'modules'` here means the build was run without
`--collect-submodules modules` — see [Building a Standalone
Executable](#building-a-standalone-executable).

**Packaged `.exe` runs but Configuration Editor changes don't persist**
Confirms the exe was built with `--onefile` instead of `--onedir`, or that
`configEditor.py`'s `_get_local_config_path()` is deriving its path from
`config.__file__` instead of `config.BASE_DIR`. See [Building a Standalone
Executable](#building-a-standalone-executable) for the correct setup.

---

## Notes

- `MOVE_FILES = False` by default. Always verify results in copy mode first.
- `batchPrinter.py` is Windows-only. It will not run on macOS or Linux.
- OCR is optional across all modules. Missing `pytesseract`/`pdf2image` prints a warning but does not prevent the toolkit from running.
- All state in `batchPrinter` is scoped to each `run()` call — running batch print twice in one session starts completely clean.
- The destination folder in the PDF Scanner is automatically excluded from the walk even when it is inside the search root, preventing an infinite copy loop.
- Batch Print prints only **page 1** of each PDF by design (`-dFirstPage=1 -dLastPage=1`), intended for cover-page/letterhead printing rather than full-document printing.