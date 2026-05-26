#!/usr/bin/env python3
"""Extract old translation files from git with proper UTF-8 encoding."""

import subprocess
import sys
from pathlib import Path

COMMIT = "9d08afb"
LANGUAGES = ["ar", "es", "fa", "fr", "pt", "ru", "sw", "zh"]
OUTPUT_DIR = Path(r"C:\Users\azvol\AppData\Local\Temp\old_translations_fixed")

def main():
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Extracting old PO files from commit {COMMIT}...")
    print(f"Output directory: {OUTPUT_DIR}")
    print()
    
    for lang in LANGUAGES:
        git_path = f"trendsearth_ui/i18n/translations/{lang}/LC_MESSAGES/messages.po"
        output_file = OUTPUT_DIR / f"{lang}.po"
        
        print(f"Extracting {lang}...", end=" ")
        
        try:
            # Use git show to extract the file content
            result = subprocess.run(
                ["git", "show", f"{COMMIT}:{git_path}"],
                capture_output=True,
                check=True,
            )
            
            # Write the bytes directly to file (they're already UTF-8)
            output_file.write_bytes(result.stdout)
            
            file_size = output_file.stat().st_size
            print(f"✓ ({file_size:,} bytes)")
            
        except subprocess.CalledProcessError as e:
            print(f"✗ Error: {e}")
            return 1
    
    print()
    print("✅ Extraction complete!")
    print(f"Files extracted to: {OUTPUT_DIR}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
