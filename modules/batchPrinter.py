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

# ── Helpers ───────────────────────────────────────────────────────────────────

def natural_sort_key(text: str):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]

def print_pdf(pdf_path: str) -> None:
    result = subprocess.run([
        GHOSTSCRIPT_PATH,
        "-q",
        "-dPrinted", "-dBATCH", "-dNOPAUSE", "-dSAFER",
        "-sDEVICE=mswinpr2",
        f"-sOutputFile=%printer%{PRINTER_NAME}",
        "-sPAPERSIZE=letter",
        "-dFIXEDMEDIA",
        "-dPDFFitPage",
        "-dFirstPage=1", "-dLastPage=1",
        pdf_path
    ], capture_output=True, text=True)
    if result.returncode != 0:
        err_msg = result.stderr.strip() or result.stdout.strip() or f"Exit code {result.returncode}"
        print(f"⚠️  Ghostscript error: {err_msg}")
        raise subprocess.CalledProcessError(result.returncode, result.args, stderr=result.stderr)

def get_jobs() -> list:
    h = win32print.OpenPrinter(PRINTER_NAME)
    jobs = win32print.EnumJobs(h, 0, -1, 1)
    win32print.ClosePrinter(h)
    return jobs

def safe_get_jobs(retries: int = 3) -> list:
    for attempt in range(retries):
        try:
            return get_jobs()
        except Exception as e:
            print(f"\n⚠️  Printer error: {e}")
            if attempt < retries - 1:
                print(f"🔄 Retrying... ({attempt + 1}/{retries})")
                time.sleep(5)
    print("❌ Printer unreachable after retries. Returning empty job list.")
    return []

def clear_screen() -> None:
    subprocess.call("cls", shell=True)

def log_history(pdf_folder: str, completed_files: list) -> None:
    log_path = os.path.join(pdf_folder, "print_history.txt")
    with open(log_path, "w") as f:
        f.write("PRINT HISTORY\n")
        f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-" * 40 + "\n")
        if completed_files:
            for i, file in enumerate(completed_files, 1):
                f.write(f"   {i}. {file}\n")
        else:
            f.write("   (none)\n")

def render_dashboard(pdfs: list, total: int, completed_files: list,
                     tracking: dict, jobs: list) -> None:
    clear_screen()
    print("🖨️  LIVE PRINTER TASK MANAGER\n")

    active_files = [f for f, v in tracking.items() if v != "DONE"]
    current = active_files[0] if active_files else "Idle"

    print(f"📦 Progress: {len(completed_files)}/{total}")
    print(f"📄 Current file: {current}")
    print(f"📊 Queue size: {len(jobs)}")
    print(f"🚦 Active Jobs: {[j['JobId'] for j in jobs]}")
    print(f"⚙️  MAX_ALLOWED_JOBS: {MAX_ACTIVE_JOBS}")

    print("\n🧾 Spooler Jobs:")
    for j in jobs:
        print(f"   - Job {j['JobId']} | {j['pDocument']}")

    print("\n🟢 Finished Prints History:")
    if completed_files:
        for i, f in enumerate(completed_files, 1):
            print(f"   {i}. {f}")
    else:
        print("   (none)")

    print("\nCTRL + C to stop\n")

def wait_for_slot() -> None:
    while True:
        jobs = safe_get_jobs()
        if len(jobs) < MAX_ACTIVE_JOBS:
            break
        time.sleep(1)

def check_completed_jobs(pdfs: list, tracking: dict, completed_files: list,
                         jobs: list) -> None:
    active_ids = {j["JobId"] for j in jobs}
    for file, job_id in list(tracking.items()):
        if job_id == "DONE":
            continue
        if isinstance(job_id, int) and job_id not in active_ids:
            tracking[file] = "DONE"
            if file not in completed_files:
                idx = next(
                    (i for i, f in enumerate(completed_files)
                     if pdfs.index(f.replace(" [FAILED]", "")) > pdfs.index(file)),
                    len(completed_files)
                )
                completed_files.insert(idx, file)

# ── Entry point ───────────────────────────────────────────────────────────────
def _validate_environment() -> bool:
    """Verify Ghostscript and the target printer exist before starting a batch run."""
    if not os.path.isfile(GHOSTSCRIPT_PATH):
        print(f"❌ Ghostscript not found at: {GHOSTSCRIPT_PATH}")
        print("   Update GHOSTSCRIPT_PATH in config.py to match your installed version.")
        return False

    try:
        printers = [p[2] for p in win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS, None, 1
        )]
    except Exception as e:
        print(f"❌ Could not enumerate printers: {e}")
        return False

    if PRINTER_NAME not in printers:
        print(f"❌ Printer '{PRINTER_NAME}' not found in Windows printer list.")
        print("   Available printers:")
        for p in printers:
            print(f"     - {p}")
        print("   Update PRINTER_NAME in config.py to match exactly.")
        return False

    return True
    

def run(pdf_folder: str) -> None:
    if not WIN32_AVAILABLE:
        print("Error: pywin32 is required for batch printing. Run: pip install pywin32")
        return
    
    if not _validate_environment():
        return

    tracking: dict        = {}
    completed_files: list = []

    pdfs = sorted(
        [f for f in os.listdir(pdf_folder) if f.lower().endswith(".pdf")],
        key=natural_sort_key
    )

    if not pdfs:
        print("No PDFs found.")
        return

    total = len(pdfs)

    for file in pdfs:
        full_path = os.path.join(pdf_folder, file)

        wait_for_slot()

        jobs = safe_get_jobs()
        render_dashboard(pdfs, total, completed_files, tracking, jobs)

        before = {j["JobId"] for j in jobs}

        try:
            print_pdf(full_path)
        except Exception as e:
            print(f"\n❌ Failed to print {file}: {e}")
            tracking[file] = "DONE"
            idx = next(
                (i for i, f in enumerate(completed_files)
                 if pdfs.index(f.replace(" [FAILED]", "")) > pdfs.index(file)),
                len(completed_files)
            )
            completed_files.insert(idx, f"{file} [FAILED]")
            time.sleep(2)
            continue

        time.sleep(0.5)

        after    = {j["JobId"] for j in safe_get_jobs()}
        new_jobs = list(after - before)
        tracking[file] = new_jobs[0] if new_jobs else -1

        for _ in range(6):
            time.sleep(0.5)
            jobs = safe_get_jobs()
            render_dashboard(pdfs, total, completed_files, tracking, jobs)
            check_completed_jobs(pdfs, tracking, completed_files, jobs)

    drain_start   = time.time()
    DRAIN_TIMEOUT = 120

    while any(v != "DONE" for v in tracking.values()):
        if time.time() - drain_start > DRAIN_TIMEOUT:
            print("\n⚠️  Drain timeout reached. Some jobs may still be pending.")
            break
        jobs = safe_get_jobs()
        check_completed_jobs(pdfs, tracking, completed_files, jobs)
        render_dashboard(pdfs, total, completed_files, tracking, jobs)
        time.sleep(0.5)

    clear_screen()
    print("✅ ALL PRINT JOBS COMPLETED\n")
    print("🟢 Finished Prints History:")
    if completed_files:
        for i, f in enumerate(completed_files, 1):
            print(f"   {i}. {f}")
    else:
        print("   (none)")

    log_history(pdf_folder, completed_files)
    print(f"\nHistory saved to: {os.path.join(pdf_folder, 'print_history.txt')}")