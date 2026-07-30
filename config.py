"""
Centralized configuration for the PDF Processing Toolkit.

All paths, constants, and settings used by the modules are defined here.
To customize without editing this file, create a ``config_local.json`` in
the project root — any matching keys will override the defaults below.

Example ``config_local.json``::

    {
        "TESSERACT_PATH": "D:\\Tools\\tesseract\\tesseract.exe",
        "MAX_WORKERS": 8,
        "OCR_DPI": 200
    }
"""

import json
import os
import sys

# ============================================================
#  BASE DIRECTORY (works both from source and when frozen)
# ============================================================
# When PyInstaller builds a --onedir exe, sys.executable is the real,
# stable exe path on disk (unlike sys._MEIPASS in --onefile, which is a
# temp folder that gets deleted on exit). Everything bundled — vendor
# tools, config_local.json — lives next to that exe.
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

VENDOR_DIR = os.path.join(BASE_DIR, "vendor")

# ============================================================
#  EXTERNAL TOOL PATHS
# ============================================================
# Prefer the bundled copy in vendor/. Fall back to a normal machine
# install if vendor/ isn't present (e.g. running from source on a dev
# machine that already has these tools installed system-wide).
_VENDOR_TESSERACT = os.path.join(VENDOR_DIR, "tesseract", "tesseract.exe")
_VENDOR_POPPLER   = os.path.join(VENDOR_DIR, "poppler", "bin")
_VENDOR_GS        = os.path.join(VENDOR_DIR, "ghostscript", "bin", "gswin64c.exe")

TESSERACT_PATH = _VENDOR_TESSERACT if os.path.isfile(_VENDOR_TESSERACT) \
    else r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = _VENDOR_POPPLER if os.path.isdir(_VENDOR_POPPLER) \
    else r"C:\poppler-26.02.0\Library\bin"
GHOSTSCRIPT_PATH = _VENDOR_GS if os.path.isfile(_VENDOR_GS) \
    else r"C:\Program Files\gs\gs10.07.1\bin\gswin64c.exe"

# Tesseract needs to find its tessdata folder (language files). If we're
# using the bundled copy, point it there explicitly rather than relying
# on tesseract's own relative-path guessing.
_VENDOR_TESSDATA = os.path.join(VENDOR_DIR, "tesseract", "tessdata")
if os.path.isdir(_VENDOR_TESSDATA):
    os.environ["TESSDATA_PREFIX"] = _VENDOR_TESSDATA

# ============================================================
#  PDF PROCESSING DEFAULTS
# ============================================================
MAX_WORKERS    = 4        # Parallel workers for extraction/matching
MAX_PAGES      = 5        # Max pages to scan per PDF
TEXT_THRESHOLD = 50       # Min chars before trying next extraction method
OCR_DPI        = 150      # DPI for OCR rendering (faster)
OCR_DPI_HIGH   = 300      # Higher DPI for accuracy-critical OCR (brand reader)

# ============================================================
#  DOCUMENT SCANNER SETTINGS
# ============================================================
SEARCH_ROOT     = ""       # Drive/folder to scan. Leave empty to be prompted.
DEST_FOLDER     = ""       # Where matched PDFs go. Leave empty to be prompted.
SCAN_LOG_FILE   = "scan_results.txt"
FILE_TIMEOUT    = 30       # Seconds before giving up on a single PDF
MIN_FILE_SIZE   = 1_024    # Skip PDFs smaller than this in bytes
MAX_FILE_SIZE   = 0        # Skip PDFs larger than this in bytes. 0 = no limit.
MOVE_FILES      = False    # True = move, False = copy
SKIP_HIDDEN     = True     # Skip hidden/system folders
SKIP_DUPLICATES = True     # Skip files whose content was already copied
MATCH_THRESHOLD = 2        # Minimum regex pattern hits required

# ============================================================
#  BRAND READER SETTINGS
# ============================================================
BRAND_LOG_FILE = "brand_results.xlsx"

# ============================================================
#  BATCH PRINTER SETTINGS
# ============================================================
PRINTER_NAME    = "DocuPrint M455 df"
MAX_ACTIVE_JOBS = 2

# ============================================================
#  OPTIONAL LOCAL OVERRIDES
# ============================================================
_LOCAL_CONFIG = os.path.join(BASE_DIR, "config_local.json")
if os.path.isfile(_LOCAL_CONFIG):
    try:
        with open(_LOCAL_CONFIG, encoding="utf-8") as _f:
            _overrides = json.load(_f)
        for _key, _val in _overrides.items():
            _upper = _key.upper()
            if _upper in globals():
                globals()[_upper] = _val
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Warning: Could not load config_local.json — {exc}")