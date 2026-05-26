import sys
import re
import os
import shutil
import hashlib
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed, TimeoutError as FuturesTimeout


missing = []
try:
    from pypdf import PdfReader
    import pdfplumber
except ImportError:
    missing.append("pypdf pdfplumber")

if missing:
    print(f"Missing dependencies. Run: pip install {' '.join(missing)}")
    sys.exit(1)

# ============================================================
#  CONFIGURATION
# ============================================================
SEARCH_ROOT     = ""       # Drive/folder to scan. Leave empty to be prompted.
DEST_FOLDER     = ""       # Where matched PDFs go. Leave empty to be prompted.
LOG_FILE        = "scan_results.txt"
MAX_WORKERS     = 4        # Parallel workers (ProcessPool — bypasses GIL for CPU work)
MAX_PAGES       = 5        # Max pages to scan per PDF
TEXT_THRESHOLD  = 50       # Min chars before trying next extraction method
FILE_TIMEOUT    = 30       # Seconds before giving up on a single PDF
MIN_FILE_SIZE   = 1_024    # Skip PDFs smaller than 1 KB (likely empty/corrupt)
MAX_FILE_SIZE   = 0        # Skip PDFs larger than this in bytes. 0 = no limit.
MOVE_FILES      = False    # True = move, False = copy (safer for testing)
SKIP_HIDDEN     = True     # Skip hidden/system folders
SKIP_DUPLICATES = True     # Skip files whose content was already copied
TESSERACT_PATH  = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH    = r"C:\poppler-26.02.0\Library\bin"
OCR_DPI         = 150      # Reduced from 300 — still readable, ~4x faster render
# ============================================================

try:
    import pytesseract
    from pdf2image import convert_from_path
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# ── Identifiers ──────────────────────────────────────────────────────────────
# A PDF qualifies only when BOTH conditions are true:
#   1. At least ONE keyword in KEYWORDS is found in the text (case-insensitive)
#   2. At least MATCH_THRESHOLD of the MATCHERS regex patterns also match
KEYWORDS = [
    
    "Certificate of Product Registration",
    "Certificate of Listing of Identical Drug Product",
]

MATCHERS = [
    re.compile(r'Brand\s*Name\s*[:\-]',                                 re.IGNORECASE),
    re.compile(r'Registration\s*Number\s*[:\-]\s*[A-Z0-9\-]+',         re.IGNORECASE),
    re.compile(r'FDA\s+Registration\s+No\.?\s*[:\-]\s*[A-Z0-9\-]+',    re.IGNORECASE),
    re.compile(r'valid\s+until\s+\d{1,2}\s+\w+\s+\d{4}',               re.IGNORECASE),
    re.compile(r'Manufacturer\s*[:\-\d]',                                re.IGNORECASE),
    re.compile(r'Importer\s*(?:/\s*Distributor)?\s*[:\-\d]',            re.IGNORECASE),
]

# How many regex patterns must match (in addition to all keywords)
MATCH_THRESHOLD = 2


# ── Per-page early exit ──────────────────────────────────────────────────────
# AND logic: a PDF qualifies only when every keyword is found AND at least
# MATCH_THRESHOLD regex patterns match.
# Pages are consumed one at a time; exits as soon as both conditions are met.

def _pages_match_early(page_texts) -> tuple[bool, int]:
    """
    Consume page_texts (iterator) one page at a time.
    Accumulates keyword hits and regex hits across pages.
    Returns (matched, regex_hit_count) the moment both conditions are
    satisfied (any one keyword found AND regex threshold met),
    or after all pages if either condition is never met.
    """
    keywords_lower  = [k.lower() for k in KEYWORDS]
    keywords_found  : set[int] = set()
    patterns_found  : set[int] = set()

    # Collect all pages first so we can check both conditions together.
    # Early exit fires the moment both are satisfied mid-page-list.
    for text in page_texts:
        if not text:
            continue
        text_lower = text.lower()

        for i, kw in enumerate(keywords_lower):
            if i not in keywords_found and kw in text_lower:
                keywords_found.add(i)

        for i, pattern in enumerate(MATCHERS):
            if i not in patterns_found and pattern.search(text):
                patterns_found.add(i)

        any_keyword_met = len(keywords_found) >= 1   # OR — any one keyword qualifies
        threshold_met   = len(patterns_found) >= MATCH_THRESHOLD

        if any_keyword_met and threshold_met:
            return True, len(patterns_found)

    return False, len(patterns_found)


def _pypdf_page_texts(pdf_path: str):
    """Yield page text strings from pypdf, up to MAX_PAGES."""
    reader = PdfReader(pdf_path)
    for page in reader.pages[:MAX_PAGES]:
        yield page.extract_text() or ""


def _pdfplumber_page_texts(pdf_path: str):
    """Yield page text strings from pdfplumber, up to MAX_PAGES."""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:MAX_PAGES]:
            yield page.extract_text() or ""


def _ocr_page_texts(pdf_path: str):
    """Yield OCR'd text per page. Only called as last resort."""
    images = convert_from_path(
        pdf_path, first_page=1, last_page=MAX_PAGES,
        poppler_path=POPPLER_PATH, dpi=OCR_DPI,
    )
    for img in images:
        yield pytesseract.image_to_string(img, config="--psm 6")


# ── Main match function ──────────────────────────────────────────────────────

def is_match(pdf_path: str) -> tuple[bool, int, str | None]:
    """
    Returns (matched, match_count, error).
    Tries pypdf first page-by-page with early exit,
    falls back to pdfplumber if text yield is too low,
    falls back to OCR only if text is still below threshold.
    """
    try:
        # ── Pass 1: pypdf (fastest) ──────────────────────────
        pages = list(_pypdf_page_texts(pdf_path))
        total_chars = sum(len(t) for t in pages)

        if total_chars >= TEXT_THRESHOLD:
            matched, count = _pages_match_early(iter(pages))
            if matched:
                return True, count, None
            # Has text but didn't match — no point trying pdfplumber or OCR
            return False, count, None

        # ── Pass 2: pdfplumber (better layout handling) ──────
        plumber_pages = list(_pdfplumber_page_texts(pdf_path))
        plumber_chars = sum(len(t) for t in plumber_pages)

        if plumber_chars >= TEXT_THRESHOLD:
            matched, count = _pages_match_early(iter(plumber_pages))
            if matched:
                return True, count, None
            return False, count, None

        # ── Pass 3: OCR (last resort — image-based PDFs) ─────
        if OCR_AVAILABLE:
            matched, count = _pages_match_early(_ocr_page_texts(pdf_path))
            return matched, count, None

        return False, 0, None

    except Exception as e:
        return False, 0, str(e)


# ── File size pre-filter ─────────────────────────────────────────────────────
# Eliminates obviously useless files before any PDF parsing begins.

def size_ok(pdf_path: str) -> bool:
    try:
        size = os.path.getsize(pdf_path)
        if size < MIN_FILE_SIZE:
            return False
        if MAX_FILE_SIZE and size > MAX_FILE_SIZE:
            return False
        return True
    except OSError:
        return False


# ── Content hash ─────────────────────────────────────────────────────────────
# SHA-256 of the first 512 KB is fast and collision-proof for practical use.
# Full-file hash is used for small files; partial for large ones to keep speed.

HASH_SAMPLE_BYTES = 512 * 1024  # 512 KB

def file_hash(pdf_path: str) -> str | None:
    try:
        h = hashlib.sha256()
        size = os.path.getsize(pdf_path)
        with open(pdf_path, "rb") as f:
            if size <= HASH_SAMPLE_BYTES:
                h.update(f.read())
            else:
                # Hash first + last chunk to catch both header and content diffs
                h.update(f.read(HASH_SAMPLE_BYTES // 2))
                f.seek(-(HASH_SAMPLE_BYTES // 2), 2)
                h.update(f.read())
        return h.hexdigest()
    except OSError:
        return None


# ── Drive walk ───────────────────────────────────────────────────────────────

HIDDEN_PREFIXES = (".", "$", "~")
SKIP_DIRS = {"system volume information", "windows", "winnt", "program files",
             "program files (x86)", "programdata"}

def walk_pdfs(root: str, exclude: str = ""):
    # Resolve both paths so comparison is reliable regardless of trailing
    # slashes, relative paths, or mixed case (important on Windows).
    abs_root    = os.path.realpath(root)
    abs_exclude = os.path.realpath(exclude) if exclude else None

    for dirpath, dirnames, filenames in os.walk(abs_root):
        print(f"  Scanning: {dirpath}", end="\r", flush=True)
        abs_dirpath = os.path.realpath(dirpath)

        # Prune destination folder so os.walk never descends into it.
        # Prevents re-reading already-copied files when dest is inside root.
        if abs_exclude:
            dirnames[:] = [
                d for d in dirnames
                if os.path.realpath(os.path.join(abs_dirpath, d)) != abs_exclude
            ]

        if SKIP_HIDDEN:
            dirnames[:] = [
                d for d in dirnames
                if not d.startswith(HIDDEN_PREFIXES)
                and d.lower() not in SKIP_DIRS
            ]

        for name in filenames:
            if name.lower().endswith(".pdf"):
                full = os.path.join(dirpath, name)
                # Also skip any PDF sitting directly in the destination folder
                if abs_exclude and os.path.realpath(full).startswith(abs_exclude):
                    continue
                if size_ok(full):
                    yield full


# ── Move / copy ──────────────────────────────────────────────────────────────

def safe_destination(dest_folder: str, filename: str) -> str:
    dest = os.path.join(dest_folder, filename)
    if not os.path.exists(dest):
        return dest
    base, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(dest):
        dest = os.path.join(dest_folder, f"{base}({counter}){ext}")
        counter += 1
    return dest

def transfer_file(src: str, dest_folder: str) -> str:
    dest = safe_destination(dest_folder, os.path.basename(src))
    if MOVE_FILES:
        shutil.move(src, dest)
    else:
        shutil.copy2(src, dest)
    return dest


# ── Worker (runs in subprocess — avoids GIL for CPU-bound extraction) ────────

def process_file(args: tuple) -> dict:
    """Top-level function required for ProcessPoolExecutor pickling."""
    pdf_path, dest_folder = args
    matched, count, error = is_match(pdf_path)
    result = {
        "path":    pdf_path,
        "matched": matched,
        "count":   count,
        "dest":    None,
        "error":   error,
    }
    if matched and not error:
        try:
            result["dest"] = transfer_file(pdf_path, dest_folder)
        except Exception as e:
            result["error"] = f"Transfer failed: {e}"
            result["matched"] = False
    return result


# ── Main ─────────────────────────────────────────────────────────────────────

def run(search_root: str, dest_folder: str) -> None:
    os.makedirs(dest_folder, exist_ok=True)
    log_path = os.path.join(dest_folder, LOG_FILE)

    print(f"Scanning   : {search_root}")
    print(f"Destination: {dest_folder}")
    print(f"Mode       : {'MOVE' if MOVE_FILES else 'COPY'}")
    print(f"Workers    : {MAX_WORKERS} (process pool)")
    print(f"Keywords   : {KEYWORDS}")
    print(f"Threshold  : {MATCH_THRESHOLD} of {len(MATCHERS)} regex patterns")
    print(f"OCR        : {'enabled' if OCR_AVAILABLE else 'disabled (install pytesseract + pdf2image)'}\n")

    seen_hashes: set[str] = set()  # tracks content hashes to skip true duplicates
    print("Walking file system and processing concurrently...\n")
    all_pdfs  = walk_pdfs(search_root, exclude=dest_folder)  # generator — no list()
    total     = 0  # incremented as files are discovered

    matched_files = []
    skipped_files = []
    error_files   = []
    processed     = 0

    # ProcessPoolExecutor: each worker is a separate Python process.
    # Bypasses the GIL — CPU-bound PDF parsing and OCR run truly in parallel.
    duplicate_files = []

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures: dict = {}

        # Stream paths from the walker directly into the pool as they are
        # discovered — walk and process run concurrently instead of
        # waiting for the full walk to finish before any work begins.
        for pdf_path in all_pdfs:

            # Duplicate check in main process (can't share sets across workers)
            if SKIP_DUPLICATES:
                h = file_hash(pdf_path)
                if h is not None and h in seen_hashes:
                    duplicate_files.append(pdf_path)
                    total -= 1  # keep total count accurate
                    continue
                if h:
                    seen_hashes.add(h)

            total += 1
            future = executor.submit(process_file, (pdf_path, dest_folder))
            futures[future] = pdf_path

        # Drain completed futures
        for future in as_completed(futures):
            processed += 1
            try:
                r = future.result(timeout=FILE_TIMEOUT)
            except FuturesTimeout:
                path = futures[future]
                error_files.append((path, "Timed out"))
                print(f"  [TIMEOUT] ({processed}/{total})  {os.path.basename(path)}")
                continue
            except Exception as e:
                path = futures[future]
                error_files.append((path, str(e)))
                print(f"  [ERROR]   ({processed}/{total})  {os.path.basename(path)}  → {e}")
                continue

            bar = f"({processed}/{total})"
            if r["error"] and not r["matched"]:
                error_files.append((r["path"], r["error"]))
                print(f"  [ERROR]   {bar}  {os.path.basename(r['path'])}  → {r['error']}")
            elif r["matched"]:
                matched_files.append((r["path"], r["dest"]))
                action = "MOVED" if MOVE_FILES else "COPIED"
                print(f"  [{action}]  {bar}  {os.path.basename(r['path'])}  [hits: {r['count']}]")
            else:
                skipped_files.append(r["path"])
                if processed % 50 == 0:
                    print(f"  [skip]    {bar}  (last: {os.path.basename(r['path'])})")

        if duplicate_files:
            print(f"\nSkipped {len(duplicate_files)} duplicate(s) (same content, different path).")

    # ── Write log ────────────────────────────────────────────
    with open(log_path, "w", encoding="utf-8") as log:
        log.write(f"PDF Scan & {'Move' if MOVE_FILES else 'Copy'} Report\n")
        log.write(f"Run at    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"Root      : {os.path.abspath(search_root)}\n")
        log.write(f"Dest      : {os.path.abspath(dest_folder)}\n")
        log.write(f"Mode      : {'MOVE' if MOVE_FILES else 'COPY'}\n")
        log.write(f"OCR       : {'enabled' if OCR_AVAILABLE else 'disabled'}\n")
        log.write(f"Workers   : {MAX_WORKERS}\n")
        log.write("=" * 70 + "\n\n")

        log.write(f"MATCHED & TRANSFERRED ({len(matched_files)})\n")
        log.write("-" * 70 + "\n")
        for src, dst in matched_files:
            log.write(f"  SRC: {src}\n  DST: {dst}\n\n")

        log.write(f"\nSKIPPED — no match ({len(skipped_files)})\n")
        log.write("-" * 70 + "\n")
        for path in skipped_files:
            log.write(f"  {path}\n")

        log.write(f"\nDUPLICATES SKIPPED ({len(duplicate_files)})\n")
        log.write("-" * 70 + "\n")
        for path in duplicate_files:
            log.write(f"  {path}\n")

        log.write(f"\nERRORS ({len(error_files)})\n")
        log.write("-" * 70 + "\n")
        for path, err in error_files:
            log.write(f"  {path}\n  → {err}\n\n")

        log.write("\n" + "=" * 70 + "\n")
        log.write(f"Total scanned : {total}\n")
        log.write(f"Transferred   : {len(matched_files)}\n")
        log.write(f"Skipped       : {len(skipped_files)}\n")
        log.write(f"Duplicates    : {len(duplicate_files)}\n")
        log.write(f"Errors        : {len(error_files)}\n")

    print(f"\n{'='*50}")
    print(f"Scanned    : {total}")
    print(f"Transferred: {len(matched_files)}")
    print(f"Skipped    : {len(skipped_files)}")
    print(f"Duplicates : {len(duplicate_files)}")
    print(f"Errors     : {len(error_files)}")
    print(f"Log        : {log_path}")


if __name__ == "__main__":
    # Required guard for ProcessPoolExecutor on Windows
    root = SEARCH_ROOT.strip()
    if not root:
        root = input("Enter the drive or folder to scan (e.g. C:\\ or D:\\docs): ").strip().strip('"')

    dest = DEST_FOLDER.strip()
    if not dest:
        dest = input("Enter the destination folder for matched PDFs: ").strip().strip('"')

    if not os.path.exists(root):
        print(f"Error: '{root}' does not exist.")
        sys.exit(1)

    run(root, dest)