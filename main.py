import sys
import os

# ── Module registry ───────────────────────────────────────────────────────────
# To add a new feature:
#   1. Create modules/your_module.py with a run() function
#   2. Import it below
#   3. Add an entry to MENU and a launcher to LAUNCHERS

import modules.documentManager  as pdf_scanner
import modules.brandReader as brand_reader
import modules.batchPrinter  as batch_print

MENU = [
    "Scan drive and copy matching PDFs       (pdf_scanner)",
    "Extract brand names to Excel            (brand_reader)",
    "Batch print PDFs to printer             (batch_print)",
]


# ── Display ───────────────────────────────────────────────────────────────────

def print_menu():
    print("\n" + "=" * 55)
    print("  PDF Processing Toolkit")
    print("=" * 55)
    for i, label in enumerate(MENU, 1):
        print(f"  {i}. {label}")
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
    print("\n── PDF Scanner ──────────────────────────────────────")
    root = prompt_path("Enter drive or folder to scan (e.g. C:\\ or D:\\docs)", must_exist=True)
    dest = prompt_path("Enter destination folder for matched PDFs",             must_exist=False)
    pdf_scanner.run(root, dest)

def launch_brand_reader():
    print("\n── Brand Reader ─────────────────────────────────────")
    folder = prompt_path("Enter folder containing PDFs", must_exist=True)
    brand_reader.run(folder)

def launch_batch_print():
    print("\n── Batch Print ──────────────────────────────────────")
    folder = prompt_path("Enter folder containing PDFs to print", must_exist=True)
    batch_print.run(folder)


LAUNCHERS = [
    launch_pdf_scanner,
    launch_brand_reader,
    launch_batch_print,
]


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    while True:
        print_menu()
        choice = input("Select an option: ").strip()

        if choice == "0":
            print("Goodbye.")
            sys.exit(0)

        if not choice.isdigit() or not (1 <= int(choice) <= len(MENU)):
            print(f"  Invalid option. Enter a number between 0 and {len(MENU)}.")
            continue

        LAUNCHERS[int(choice) - 1]()

        input("\nPress Enter to return to the menu...")


if __name__ == "__main__":
    main()