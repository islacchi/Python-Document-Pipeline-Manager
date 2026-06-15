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
- [Modules](#modules)
  - [1. PDF Scanner](#1-pdf-scanner)
  - [2. Brand Reader](#2-brand-reader)
  - [3. Batch Print](#3-batch-print)
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
    └── batchPrinter.py       ← batch prints PDFs to a physical printer
```

> Module files use the names above, matching the imports in `main.py`
> (`modules.documentManager`, `modules.brandReader`, `modules.batchPrinter`).

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
   `TESSERACT_PATH` / `POPPLER_PATH` in `config.py`.

4. For batch printing, install Ghostscript:
   Download from https://www.ghostscript.com/releases/gsdnld.html and update
   `GHOSTSCRIPT_PATH` in `config.py` to match the installed `gswin64c.exe` path.

5. Set `PRINTER_NAME` in `config.py` to the exact printer name as registered
   in Windows (Settings → Bluetooth & devices → Printers & scanners). This is
   checked automatically at the start of every batch print run — see
   [Batch Print](#3-batch-print) below.

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
  0. Exit
=======================================================
```

Select an option by typing the number and pressing Enter. After each
operation completes, press Enter to return to the menu.

If a module's dependencies are missing, its menu entry is marked
`⚠ missing deps` and selecting it prints the required `pip install` command
instead of running.

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

---

## Notes

- `MOVE_FILES = False` by default. Always verify results in copy mode first.
- `batchPrinter.py` is Windows-only. It will not run on macOS or Linux.
- OCR is optional across all modules. Missing `pytesseract`/`pdf2image` prints a warning but does not prevent the toolkit from running.
- All state in `batchPrinter` is scoped to each `run()` call — running batch print twice in one session starts completely clean.
- The destination folder in the PDF Scanner is automatically excluded from the walk even when it is inside the search root, preventing an infinite copy loop.
- Batch Print prints only **page 1** of each PDF by design (`-dFirstPage=1 -dLastPage=1`), intended for cover-page/letterhead printing rather than full-document printing.