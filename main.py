import sys
import os
import logging
import importlib

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("toolkit")

# ── Config ─────────────────────────────────────────────────────────────────────
import config  # noqa: E402, F401

# ── Module registry ───────────────────────────────────────────────────────────
# To add a new feature:
#   1. Create modules/your_module.py with a run() function
#   2. Import it below
#   3. Add an entry to MENU and a launcher to LAUNCHERS


def _try_import(module_path: str):
    """Import a module, returning *None* if its dependencies are missing."""
    try:
        return importlib.import_module(module_path)
    except SystemExit:
        # Some modules call sys.exit(1) on ImportError — treat as unavailable
        return None


pdf_scanner  = _try_import("modules.documentManager")
brand_reader = _try_import("modules.brandReader")
batch_print  = _try_import("modules.batchPrinter")

# ── Menu definitions ──────────────────────────────────────────────────────────
# Each entry is (label, module_or_None, launcher_func_or_None).

MENU_ENTRIES = [
    (
        "Scan drive and copy matching PDFs       (pdf_scanner)",
        pdf_scanner,
        "launch_pdf_scanner",
    ),
    (
        "Extract brand names to Excel            (brand_reader)",
        brand_reader,
        "launch_brand_reader",
    ),
    (
        "Batch print PDFs to printer             (batch_print)",
        batch_print,
        "launch_batch_print",
    ),
]


# ── Display ───────────────────────────────────────────────────────────────────

def print_menu():
    print("\n" + "=" * 55)
    print("  PDF Processing Toolkit")
    print("=" * 55)
    for i, (label, module, _) in enumerate(MENU_ENTRIES, 1):
        status = "" if module else "  ⚠ missing deps"
        print(f"  {i}. {label}{status}")
    print("  0. Exit")
    print("=" * 55)


# ── Prompt helpers ────────────────────────────────────────────────────────────

def prompt_path(label: str, must_exist: bool = True) -> str:
    while True:
        value = input(f"{label}: ").strip().strip('"')
        if must_exist and not os.path.exists(value):
            print(f"  Error: '{value}' does not exist. Try again.")
            continue
        return value


# ── Launchers ─────────────────────────────────────────────────────────────────
# All user prompts live here. Modules only receive ready-to-use values.

def launch_pdf_scanner():
    if pdf_scanner is None:
        _missing_deps_notice("documentManager", "pypdf pdfplumber")
        return
    print("\n── PDF Scanner ──────────────────────────────────────")
    root = prompt_path("Enter drive or folder to scan (e.g. C:\\ or D:\\docs)", must_exist=True)
    dest = prompt_path("Enter destination folder for matched PDFs",             must_exist=False)
    pdf_scanner.run(root, dest)


def launch_brand_reader():
    if brand_reader is None:
        _missing_deps_notice("brandReader", "pypdf pdfplumber openpyxl")
        return
    print("\n── Brand Reader ─────────────────────────────────────")
    folder = prompt_path("Enter folder containing PDFs", must_exist=True)
    brand_reader.run(folder)


def launch_batch_print():
    if batch_print is None:
        _missing_deps_notice("batchPrinter", "pywin32")
        return
    print("\n── Batch Print ──────────────────────────────────────")
    folder = prompt_path("Enter folder containing PDFs to print", must_exist=True)
    batch_print.run(folder)


def _missing_deps_notice(module_name: str, packages: str) -> None:
    print(f"\n  ⚠  Module '{module_name}' cannot run — missing dependencies.")
    print(f"     Install with:  pip install {packages}\n")


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    logger.info("PDF Processing Toolkit started")

    while True:
        print_menu()
        choice = input("Select an option: ").strip()

        if choice == "0":
            print("Goodbye.")
            sys.exit(0)

        if not choice.isdigit() or not (1 <= int(choice) <= len(MENU_ENTRIES)):
            print(f"  Invalid option. Enter a number between 0 and {len(MENU_ENTRIES)}.")
            continue

        _, module, launcher_name = MENU_ENTRIES[int(choice) - 1]
        if module is None:
            # Already shown in menu; give a short reminder
            print("  This module is unavailable. Check the warnings above.")
        else:
            globals()[launcher_name]()

        input("\nPress Enter to return to the menu...")


if __name__ == "__main__":
    main()