import os
import sys
import json

try:
    import config
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import config

# Define categories and configuration items
# Item format: (display_name, key, type_converter, validator_func)
def _validate_path_file(val: str) -> bool:
    if not val:
        return True
    return os.path.isfile(val)

def _validate_path_dir(val: str) -> bool:
    if not val:
        return True
    return os.path.isdir(val)

def _validate_positive_int(val: str) -> bool:
    try:
        return int(val) >= 0
    except ValueError:
        return False

def _validate_bool(val: str) -> bool:
    return val.lower() in ("y", "n", "true", "false", "yes", "no", "1", "0")

def _to_bool(val: str) -> bool:
    return val.lower() in ("y", "true", "yes", "1")

CATEGORIES = {
    1: {
        "name": "Global & Concurrency Settings (Affects All Modules)",
        "items": [
            ("Parallel Workers (Processes/Threads)", "MAX_WORKERS", int, _validate_positive_int, "Number of concurrent CPU tasks"),
            ("Max Pages to Scan per PDF", "MAX_PAGES", int, _validate_positive_int, "Limits scan to first N pages to save time")
        ]
    },
    2: {
        "name": "PDF Scanner Settings (pdf_scanner)",
        "items": [
            ("Default Search Root Path", "SEARCH_ROOT", str, lambda v: True, "Drive/folder to scan. Leave empty to prompt at runtime"),
            ("Default Destination Folder", "DEST_FOLDER", str, lambda v: True, "Where matched PDFs are copied. Leave empty to prompt"),
            ("Scanner Log File Name", "SCAN_LOG_FILE", str, lambda v: True, "Output text report filename"),
            ("Matcher Hit Threshold", "MATCH_THRESHOLD", int, _validate_positive_int, "Minimum regex hits required to match a PDF"),
            ("Move Files (Instead of Copy)", "MOVE_FILES", _to_bool, _validate_bool, "WARNING: Setting True will delete source files after copy"),
            ("Skip Duplicates (Content Hash)", "SKIP_DUPLICATES", _to_bool, _validate_bool, "True skips files whose content was already copied"),
            ("Skip Hidden & System Folders", "SKIP_HIDDEN", _to_bool, _validate_bool, "Skip dotfiles, Windows system folders, etc."),
            ("Min PDF File Size Filter (bytes)", "MIN_FILE_SIZE", int, _validate_positive_int, "Ignore PDFs smaller than this"),
            ("Max PDF File Size Filter (bytes)", "MAX_FILE_SIZE", int, _validate_positive_int, "Ignore PDFs larger than this (0 = no limit)"),
            ("File Processing Timeout (secs)", "FILE_TIMEOUT", int, _validate_positive_int, "Timeout for processing a single PDF")
        ]
    },
    3: {
        "name": "Brand Reader Settings (brand_reader)",
        "items": [
            ("Brand Reader Log File Name", "BRAND_LOG_FILE", str, lambda v: True, "Output Excel sheet report filename")
        ]
    },
    4: {
        "name": "Batch Printer Settings (batch_print)",
        "items": [
            ("Target Windows Printer Name", "PRINTER_NAME", str, lambda v: True, "Must match exact registered Windows printer name"),
            ("Max Active Print Jobs in Queue", "MAX_ACTIVE_JOBS", int, _validate_positive_int, "Saves memory by pausing loop when spooler is full"),
            ("Ghostscript Command Path", "GHOSTSCRIPT_PATH", str, _validate_path_file, "Expects full path to gswin64c.exe")
        ]
    },
    5: {
        "name": "OCR Engine Settings",
        "items": [
            ("Tesseract Executable Path", "TESSERACT_PATH", str, _validate_path_file, "Expects full path to tesseract.exe"),
            ("Poppler Library Bin Path", "POPPLER_PATH", str, _validate_path_dir, "Expects bin folder path containing pdftoppm.exe"),
            ("OCR Rendering DPI (Fast Scanner)", "OCR_DPI", int, _validate_positive_int, "DPI used for document manager OCR"),
            ("OCR Rendering DPI (High Quality)", "OCR_DPI_HIGH", int, _validate_positive_int, "DPI used for brand extraction OCR"),
            ("Text Extraction Threshold (chars)", "TEXT_THRESHOLD", int, _validate_positive_int, "Minimum text length before skipping OCR fallback")
        ]
    }
}

def _get_local_config_path() -> str:
    # config.py location is the root of the project
    config_dir = os.path.dirname(config.__file__)
    return os.path.join(config_dir, "config_local.json")

def _load_local_overrides() -> dict:
    path = _get_local_config_path()
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_local_overrides(overrides: dict) -> None:
    path = _get_local_config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(overrides, f, indent=4)
    except Exception as e:
        print(f"Error saving config_local.json: {e}")

def _sync_session_config(key: str, val) -> None:
    """Dynamically update config and all loaded modules in real-time."""
    # 1. Update config module
    setattr(config, key, val)
    
    # 2. Update variables in loaded pipeline modules
    modules_to_sync = ["modules.documentManager", "modules.brandReader", "modules.batchPrinter"]
    for mod_name in modules_to_sync:
        if mod_name in sys.modules:
            mod = sys.modules[mod_name]
            if hasattr(mod, key):
                setattr(mod, key, val)

def _prompt_edit(display_name: str, key: str, type_converter, validator, help_text: str) -> bool:
    current_val = getattr(config, key, None)
    print(f"\nEditing: {display_name} ({key})")
    print(f"Description: {help_text}")
    print(f"Current Value: {repr(current_val)}")
    
    val_input = input("Enter new value (or press Enter to cancel): ").strip()
    if not val_input:
        print("Cancelled.")
        return False
        
    if not validator(val_input):
        print("  Error: Invalid format or criteria. Try again.")
        return False
        
    converted_val = type_converter(val_input) if type_converter != str else val_input
    
    # Path warning validation
    if key in ("TESSERACT_PATH", "POPPLER_PATH", "GHOSTSCRIPT_PATH") and converted_val:
        exists = os.path.exists(converted_val)
        if not exists:
            confirm = input("  Warning: Specified path does not exist on this machine. Save anyway? (y/n): ").strip().lower()
            if confirm not in ("y", "yes"):
                print("Cancelled.")
                return False
                
    # Save overrides
    overrides = _load_local_overrides()
    overrides[key] = converted_val
    _save_local_overrides(overrides)
    
    # Apply dynamically to session
    _sync_session_config(key, converted_val)
    print(f"Successfully saved and applied setting: {key} = {converted_val}")
    return True

def run() -> None:
    while True:
        print("\n" + "=" * 55)
        print("  PDF processing toolkit — Configuration Editor")
        print("=" * 55)
        for idx, cat in CATEGORIES.items():
            print(f"  {idx}. {cat['name']}")
        print("  0. Back to Main Menu")
        print("=" * 55)
        
        choice = input("Select a category: ").strip()
        if choice == "0":
            break
            
        if not choice.isdigit() or int(choice) not in CATEGORIES:
            print("Invalid choice. Try again.")
            continue
            
        cat_idx = int(choice)
        category = CATEGORIES[cat_idx]
        
        while True:
            print(f"\n── {category['name']} ─────────────────────────────────")
            for idx, item in enumerate(category["items"], 1):
                display_name, key, _, _, _ = item
                val = getattr(config, key, None)
                print(f"  {idx}. {display_name:<36} : {repr(val)}")
            print("  0. Back")
            print("─" * 55)
            
            sub_choice = input("Select a setting to edit: ").strip()
            if sub_choice == "0":
                break
                
            if not sub_choice.isdigit() or not (1 <= int(sub_choice) <= len(category["items"])):
                print("Invalid choice. Try again.")
                continue
                
            selected_item = category["items"][int(sub_choice) - 1]
            display_name, key, converter, validator, help_text = selected_item
            _prompt_edit(display_name, key, converter, validator, help_text)
            input("\nPress Enter to continue...")
