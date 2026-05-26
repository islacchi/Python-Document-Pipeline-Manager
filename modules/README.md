# PDF Processing Toolkit

A modular command-line toolkit for processing PDF documents. Run `main.py` to access all features through a central menu.

---

## Project Structure

```
project/
├── main.py                  ← entry point and main menu
└── modules/
    ├── __init__.py
    ├── pdf_scanner.py       ← scans a drive and copies matching PDFs
    ├── brand_reader.py      ← extracts brand name fields into Excel
    └── batch_print.py       ← batch prints PDFs to a physical printer
```

---

## Requirements

### Python
Python 3.10 or higher (required for `str | None` type hint syntax).

### Dependencies

Install all Python dependencies with:
```
pip install pypdf pdfplumber openpyxl pywin32
```

| Package      | Required by                        |
|--------------|------------------------------------|
| pypdf        | pdf_scanner, brand_reader          |
| pdfplumber   | pdf_scanner, brand_reader          |
| openpyxl     | brand_reader                       |
| pywin32      | batch_print                        |

### Optional — OCR support
Required only if your PDFs are scanned images rather than digitally created.

```
pip install pytesseract pdf2image
```

You must also install the following binaries and update their paths in the relevant module config:

**Tesseract OCR**
Download: https://github.com/UB-Mannheim/tesseract/wiki
Default path expected: `C:\Program Files\Tesseract-OCR\tesseract.exe`

**Poppler**
Download: https://github.com/oschwartz10612/poppler-windows/releases
Default path expected: `C:\poppler-26.02.0\Library\bin`

---

## How to Run

```
python main.py
```

You will be presented with the following menu:

```
===================================================
  PDF Processing Toolkit
===================================================
  1. Scan drive and copy matching PDFs       (pdf_scanner)
  2. Extract brand names to Excel            (brand_reader)
  3. Batch print PDFs to printer             (batch_print)
  0. Exit
===================================================
```

---

## Modules

### 1. PDF Scanner (`modules/pdf_scanner.py`)

Walks a drive or folder recursively and copies PDFs that match a keyword and regex combination to a destination folder.

**Matching logic**

A PDF qualifies only when both conditions are true:
- At least one keyword from `KEYWORDS` is found in the extracted text (case-insensitive), AND
- At least `MATCH_THRESHOLD` of the `MATCHERS` regex patterns also match

**Default keywords**
```
Certificate of Good Manufacturing Practice
Certificate of Product Registration
Certificate of Listing of Identical Drug Product
```

**Default regex patterns (6 total, threshold: 2)**
```
Brand Name:
Registration Number:
FDA Registration No.:
Valid Until <date>
Manufacturer:
Importer / Distributor:
```

**Text extraction fallback chain**

pypdf → pdfplumber → OCR (Tesseract)

Each step is only attempted if the previous one returned insufficient text. Within each step, pages are read one at a time and extraction stops the moment the match threshold is reached.

**Duplicate handling**

Files are SHA-256 hashed (first + last 256 KB for large files) before copying. Files with identical content are skipped regardless of filename or location.

**Configuration** (top of `pdf_scanner.py`)

| Setting          | Default | Description                                      |
|------------------|---------|--------------------------------------------------|
| `MAX_WORKERS`    | 4       | Parallel worker processes                        |
| `MAX_PAGES`      | 5       | Maximum pages to scan per PDF                    |
| `FILE_TIMEOUT`   | 30      | Seconds before abandoning a single file          |
| `MIN_FILE_SIZE`  | 1024    | Skip files smaller than this (bytes)             |
| `MAX_FILE_SIZE`  | 0       | Skip files larger than this (0 = no limit)       |
| `MOVE_FILES`     | False   | True = move files, False = copy files            |
| `SKIP_DUPLICATES`| True    | Skip files with identical content                |
| `MATCH_THRESHOLD`| 2       | Minimum regex pattern hits required              |
| `OCR_DPI`        | 150     | DPI for OCR rendering (raise for low-quality scans) |
| `TESSERACT_PATH` | —       | Full path to tesseract.exe                       |
| `POPPLER_PATH`   | —       | Full path to Poppler bin folder                  |

**Output**

A `scan_results.txt` log is written to the destination folder listing every copied, skipped, duplicate, and errored file with full source → destination paths.

---

### 2. Brand Reader (`modules/brand_reader.py`)

Scans all PDFs in a single folder and extracts structured fields into a formatted Excel report.

**Fields extracted**

| Field           | Pattern matched                        |
|-----------------|----------------------------------------|
| Brand Name      | `Brand Name:`                          |
| Registration No.| `Registration Number:` / `FDA Registration No.:` |
| Valid Until     | `valid until <date>`                   |
| Manufacturer    | `Manufacturer:` / `Manufacturer Name and Address:` |
| Trader          | `Trader:`                              |
| Importer        | `Importer:` / `Importer / Distributor:` |
| Distributor     | `Distributor:`                         |

**Text extraction fallback chain**

Same as pdf_scanner: pypdf → pdfplumber → OCR (Tesseract).

**Configuration** (top of `brand_reader.py`)

| Setting          | Default | Description                        |
|------------------|---------|------------------------------------|
| `MAX_WORKERS`    | 4       | Parallel worker threads            |
| `MAX_PAGES`      | 5       | Maximum pages to scan per PDF      |
| `OCR_DPI`        | 300     | DPI for OCR rendering              |
| `TEXT_THRESHOLD` | 50      | Minimum characters before fallback |
| `TESSERACT_PATH` | —       | Full path to tesseract.exe         |
| `POPPLER_PATH`   | —       | Full path to Poppler bin folder    |

**Output**

A `brand_results.xlsx` file is written to the scanned folder. If the file already exists, it is saved as `brand_results(1).xlsx`, `brand_results(2).xlsx`, and so on. The Excel report contains three sections: FOUND, NOT FOUND, and ERRORS, with a summary row at the bottom.

---

### 3. Batch Print (`modules/batch_print.py`)

Sends all PDFs in a folder to a physical printer in natural sort order with a live dashboard showing print queue state.

**Features**
- Natural sort order (`cert2.pdf` before `cert10.pdf`)
- Respects `MAX_ACTIVE_JOBS` limit — waits for the queue to clear before sending the next file
- Detects completed jobs by tracking spooler job IDs before and after each print call
- Handles failed print jobs with `[FAILED]` tagging in the history
- Final drain loop waits for all remaining jobs to clear after the last file is sent
- Saves a `print_history.txt` log to the source folder on completion

**Configuration** (top of `batch_print.py`)

| Setting          | Default                          | Description                              |
|------------------|----------------------------------|------------------------------------------|
| `PRINTER_NAME`   | FUJI XEROX DocuPrint M455 df     | Exact printer name as shown in Windows   |
| `SUMATRA_PATH`   | —                                | Full path to SumatraPDF.exe              |
| `MAX_ACTIVE_JOBS`| 2                                | Maximum concurrent spooler jobs allowed  |

To find your exact printer name, open **Control Panel → Devices and Printers** and copy the name exactly as displayed.

SumatraPDF download: https://www.sumatrapdfreader.org/download-free-pdf-viewer

**Output**

A `print_history.txt` log is written to the PDF folder listing all printed files in order, with `[FAILED]` appended to any file that failed to send.

---

## Adding a New Module

1. Create `modules/your_module.py` with a `run()` function that accepts whatever arguments it needs.
2. Add `import modules.your_module as your_module` at the top of `main.py`.
3. Add a string entry to the `MENU` list in `main.py`.
4. Add a launcher function to `main.py` that prompts for inputs and calls `your_module.run(...)`.
5. Append that launcher function to the `LAUNCHERS` list.

The menu numbering updates automatically.

---

## Notes

- `MOVE_FILES = False` in `pdf_scanner.py` by default. Test with copy mode before switching to move.
- `batch_print.py` requires Windows and `pywin32`. It will not run on macOS or Linux.
- OCR is optional. If `pytesseract` and `pdf2image` are not installed, the toolkit falls back to text-only extraction and prints a warning on startup.
- All state in `batch_print` is local to each `run()` call — running batch print twice in the same session starts clean.