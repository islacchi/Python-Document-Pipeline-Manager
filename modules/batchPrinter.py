import os
import time
import subprocess
import re

from config import PRINTER_NAME, GHOSTSCRIPT_PATH, MAX_ACTIVE_JOBS

try:
    import win32print
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    print("Warning: win32print not available. Run: pip install pywin32")

# ── Constants ─────────────────────────────────────────────────────────────────

STATUS_PENDING = "PENDING"
STATUS_SENDING = "SENDING"
STATUS_DONE    = "DONE"
STATUS_FAILED  = "FAILED"

INTER_JOB_DELAY = 2   # seconds between dispatches — prevents printer flooding
DRAIN_TIMEOUT   = 60  # seconds to wait for spooler to clear after last job

# ── Helpers ───────────────────────────────────────────────────────────────────

def natural_sort_key(text: str):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]

def _unique_log_path(pdf_folder: str) -> str:
    """Return a non-colliding path for print_history.txt, incrementing if needed."""
    base = os.path.join(pdf_folder, "print_history.txt")
    if not os.path.exists(base):
        return base
    counter = 1
    while True:
        candidate = os.path.join(pdf_folder, f"print_history({counter}).txt")
        if not os.path.exists(candidate):
            return candidate
        counter += 1

def print_pdf(pdf_path: str) -> None:
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE

    result = subprocess.run([
        GHOSTSCRIPT_PATH,
        "-q",
        "-dNoCancel",
        "-dPrinted", "-dBATCH", "-dNOPAUSE", "-dSAFER",
        "-sDEVICE=mswinpr2",
        f"-sOutputFile=%printer%{PRINTER_NAME}",
        "-sPAPERSIZE=letter",
        "-dFIXEDMEDIA",
        "-dPDFFitPage",
        "-dFirstPage=1", "-dLastPage=1",
        pdf_path
    ], capture_output=True, text=True,
       startupinfo=startupinfo,
       creationflags=subprocess.CREATE_NO_WINDOW)

    if result.returncode != 0:
        err_msg = result.stderr.strip() or result.stdout.strip() or f"Exit code {result.returncode}"
        raise subprocess.CalledProcessError(result.returncode, result.args, stderr=err_msg)

def get_jobs() -> list:
    h = win32print.OpenPrinter(PRINTER_NAME)
    jobs = win32print.EnumJobs(h, 0, -1, 1)
    win32print.ClosePrinter(h)
    return jobs

def safe_get_jobs(retries: int = 3) -> list:
    for attempt in range(retries):
        try:
            return get_jobs()
        except Exception:
            if attempt < retries - 1:
                time.sleep(5)
    return []

def clear_screen() -> None:
    subprocess.call("cls", shell=True)

def log_history(pdf_folder: str, statuses: dict) -> str:
    """Write a non-overwriting print history log. Returns the path written."""
    log_path = _unique_log_path(pdf_folder)
    sent   = [f for f, s in statuses.items() if s == STATUS_DONE]
    failed = [f for f, s in statuses.items() if s == STATUS_FAILED]
    with open(log_path, "w", encoding="utf-8") as fh:
        fh.write("PRINT HISTORY\n")
        fh.write(f"Date   : {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        fh.write(f"Printer: {PRINTER_NAME}\n")
        fh.write("-" * 40 + "\n")
        fh.write(f"Sent ({len(sent)}):\n")
        for i, name in enumerate(sent, 1):
            fh.write(f"   {i}. {name}\n")
        if failed:
            fh.write(f"\nFailed ({len(failed)}):\n")
            for i, name in enumerate(failed, 1):
                fh.write(f"   {i}. {name}\n")
        if not sent and not failed:
            fh.write("   (none)\n")
    return log_path

# ── Dashboard ─────────────────────────────────────────────────────────────────

_STATUS_ICON = {
    STATUS_PENDING: "  ○",
    STATUS_SENDING: "  →",
    STATUS_DONE:    "  ✔",
    STATUS_FAILED:  "  ✘",
}

_STATUS_LABEL = {
    STATUS_PENDING: "pending",
    STATUS_SENDING: "sending",
    STATUS_DONE:    "sent",
    STATUS_FAILED:  "FAILED",
}

def render_dashboard(pdfs: list, statuses: dict, jobs: list) -> None:
    clear_screen()

    total     = len(pdfs)
    done      = sum(1 for s in statuses.values() if s == STATUS_DONE)
    failed    = sum(1 for s in statuses.values() if s == STATUS_FAILED)
    processed = done + failed

    # ── Header ────────────────────────────────────────────────────────────────
    print("  Batch print\n")
    print(f"  Printer : {PRINTER_NAME}")
    print("  Settings: Letter · page 1 only · natural sort")
    print()

    # ── Metrics ───────────────────────────────────────────────────────────────
    col = 22
    print(f"  {'Total':<{col}}{'Sent':<{col}}{'Failed':<{col}}")
    print(f"  {total:<{col}}{done:<{col}}{failed:<{col}}")
    print()

    # ── Progress bar ──────────────────────────────────────────────────────────
    bar_width = 50
    filled    = int(bar_width * processed / total) if total else 0
    bar       = "█" * filled + "░" * (bar_width - filled)
    pct       = int(100 * processed / total) if total else 0
    print(f"  [{bar}] {pct}%  ({processed}/{total})")
    print()

    # ── File list ─────────────────────────────────────────────────────────────
    print(f"  {'#':<5}{'File':<45}{'Status'}")
    print(f"  {'-'*4}  {'-'*43}  {'-'*8}")
    for i, pdf in enumerate(pdfs, 1):
        status = statuses.get(pdf, STATUS_PENDING)
        icon   = _STATUS_ICON[status]
        label  = _STATUS_LABEL[status]
        name   = pdf if len(pdf) <= 42 else pdf[:39] + "..."
        marker = " <" if status == STATUS_SENDING else ""
        print(f"  {i:<4} {icon}  {name:<43}  {label}{marker}")

    print()

    # ── Footer ────────────────────────────────────────────────────────────────
    slots_free = max(0, MAX_ACTIVE_JOBS - len(jobs))
    slot_info  = f"Spooler slots free: {slots_free}/{MAX_ACTIVE_JOBS}"
    print(f"  {slot_info:<40}CTRL + C to stop")

# ── Environment check ─────────────────────────────────────────────────────────

def _validate_environment() -> bool:
    if not os.path.isfile(GHOSTSCRIPT_PATH):
        print(f"  Ghostscript not found at: {GHOSTSCRIPT_PATH}")
        print("  Update GHOSTSCRIPT_PATH in config.py to match your installed version.")
        return False

    try:
        printers = [p[2] for p in win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS, None, 1
        )]
    except Exception:
        print("  Could not enumerate printers. Ensure the print spooler service is running.")
        return False

    if PRINTER_NAME not in printers:
        print(f"  Printer '{PRINTER_NAME}' not found in Windows printer list.")
        print("  Available printers:")
        for p in printers:
            print(f"    - {p}")
        print("  Update PRINTER_NAME in config.py to match exactly.")
        return False

    return True

# ── Spooler slot gate ─────────────────────────────────────────────────────────

def wait_for_slot(pdfs: list, statuses: dict) -> list:
    """Block until a spooler slot is free, refreshing the dashboard while waiting."""
    while True:
        jobs = safe_get_jobs()
        if len(jobs) < MAX_ACTIVE_JOBS:
            return jobs
        render_dashboard(pdfs, statuses, jobs)
        time.sleep(1)

# ── Entry point ───────────────────────────────────────────────────────────────

def run(pdf_folder: str) -> None:
    if not WIN32_AVAILABLE:
        print("  pywin32 is required for batch printing. Run: pip install pywin32")
        return

    if not _validate_environment():
        return

    pdfs = sorted(
        [f for f in os.listdir(pdf_folder) if f.lower().endswith(".pdf")],
        key=natural_sort_key
    )

    if not pdfs:
        print("  No PDFs found in the specified folder.")
        return

    statuses: dict = {pdf: STATUS_PENDING for pdf in pdfs}

    for file in pdfs:
        full_path = os.path.join(pdf_folder, file)

        jobs = wait_for_slot(pdfs, statuses)

        statuses[file] = STATUS_SENDING
        render_dashboard(pdfs, statuses, jobs)

        try:
            print_pdf(full_path)
            statuses[file] = STATUS_DONE
        except Exception:
            statuses[file] = STATUS_FAILED

        jobs = safe_get_jobs()
        render_dashboard(pdfs, statuses, jobs)

        # Throttle — give the printer breathing room between dispatches
        time.sleep(INTER_JOB_DELAY)

    # ── Final drain ───────────────────────────────────────────────────────────
    drain_start = time.time()
    while True:
        jobs = safe_get_jobs()
        if not jobs or time.time() - drain_start > DRAIN_TIMEOUT:
            break
        render_dashboard(pdfs, statuses, jobs)
        time.sleep(0.5)

    # ── Completion summary ────────────────────────────────────────────────────
    clear_screen()

    total  = len(pdfs)
    done   = sum(1 for s in statuses.values() if s == STATUS_DONE)
    failed = sum(1 for s in statuses.values() if s == STATUS_FAILED)

    print("  All jobs dispatched\n")
    print(f"  Sent  : {done}/{total}")
    if failed:
        print(f"  Failed: {failed}/{total}")
    print()

    # ── Print history ─────────────────────────────────────────────────────────
    sent_files   = [f for f, s in statuses.items() if s == STATUS_DONE]
    failed_files = [f for f, s in statuses.items() if s == STATUS_FAILED]

    print("  Sent:")
    if sent_files:
        for i, name in enumerate(sent_files, 1):
            print(f"    {i}. {name}")
    else:
        print("    (none)")

    if failed_files:
        print()
        print("  Failed:")
        for i, name in enumerate(failed_files, 1):
            print(f"    {i}. {name}")

    # ── Log ───────────────────────────────────────────────────────────────────
    log_path = log_history(pdf_folder, statuses)
    print(f"\n  Log saved to: {log_path}")