#!/usr/bin/env python3
"""
Personal Data Export/Sync Tool for chaits

This script helps you export/backup your private data for syncing to another machine.
Since .aiccounts/ contents are gitignored, use this to package your data for manual transfer.

Usage:
    python sync_personal_data.py                      # GUI menu (if available)
    python sync_personal_data.py export [output_path] # Create archive (GUI picker if no path)
    python sync_personal_data.py import [archive_path]# Import from archive (GUI picker if no path)
    python sync_personal_data.py list                 # List what would be exported
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime
import zipfile
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    HAS_GUI = True
except ImportError:
    HAS_GUI = False

# Directories containing private data
PRIVATE_DIRS = [
    ".aiccounts",
    "db",
    "chaits_exports",
]

ARCHIVE_NAME_TEMPLATE = "chaits_private_data_{timestamp}.zip"

def list_private_data():
    """List all private data files that would be exported"""
    print("Private data files:")
    total_size = 0
    file_count = 0
    
    for dir_path in PRIVATE_DIRS:
        path = Path(dir_path)
        if not path.exists():
            print(f"  {dir_path}/ (not found)")
            continue
            
        print(f"\n  {dir_path}/")
        if path.is_file():
            size = path.stat().st_size
            print(f"    {path.name} ({size:,} bytes)")
            total_size += size
            file_count += 1
        else:
            for item in path.rglob("*"):
                if item.is_file():
                    size = item.stat().st_size
                    rel_path = item.relative_to(path)
                    print(f"    {rel_path} ({size:,} bytes)")
                    total_size += size
                    file_count += 1
    
    print(f"\nTotal: {file_count} files, {total_size:,} bytes ({total_size / 1024 / 1024:.1f} MB)")

def export_private_data(output_path=None):
    """Create a zip archive of all private data"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_name = ARCHIVE_NAME_TEMPLATE.format(timestamp=timestamp)
    
    # Use GUI picker if no path provided and GUI available
    if output_path is None and HAS_GUI:
        root = tk.Tk()
        root.withdraw()
        output_path = filedialog.asksaveasfilename(
            title="Save chaits private data archive",
            defaultextension=".zip",
            initialfile=default_name,
            filetypes=[("ZIP archives", "*.zip"), ("All files", "*.*")]
        )
        root.destroy()
        if not output_path:  # User cancelled
            print("Export cancelled")
            return
    elif output_path is None:
        output_path = default_name
    
    archive_name = output_path
    
    print(f"Creating archive: {archive_name}")
    
    with zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for dir_path in PRIVATE_DIRS:
            path = Path(dir_path)
            if not path.exists():
                print(f"  Skipping {dir_path}/ (not found)")
                continue
                
            print(f"  Adding {dir_path}/")
            if path.is_file():
                zipf.write(path, path.name)
            else:
                for item in path.rglob("*"):
                    if item.is_file():
                        zipf.write(item, item.relative_to("."))
    
    archive_size = Path(archive_name).stat().st_size
    print(f"\n[+] Created {archive_name} ({archive_size:,} bytes, {archive_size / 1024 / 1024:.1f} MB)")
    
    if HAS_GUI:
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Export Complete", 
                          f"Created {Path(archive_name).name}\n\n"
                          f"Size: {archive_size / 1024 / 1024:.1f} MB\n\n"
                          f"To import on another machine:\n"
                          f"python sync_personal_data.py import")
        root.destroy()
    else:
        print(f"\nTo import on another machine:")
        print(f"  1. Copy {archive_name} to the chaits directory")
        print(f"  2. Run: python sync_personal_data.py import {archive_name}")

def import_private_data(archive_path=None):
    """Extract private data from archive"""
    if archive_path is None:
        # Try GUI picker if available
        if HAS_GUI:
            root = tk.Tk()
            root.withdraw()
            archive_path = filedialog.askopenfilename(
                title="Select chaits private data archive",
                filetypes=[("ZIP archives", "*.zip"), ("All files", "*.*")]
            )
            root.destroy()
            if not archive_path:  # User cancelled
                print("Import cancelled")
                return
        else:
            # Find most recent archive
            archives = list(Path(".").glob("chaits_private_data_*.zip"))
            if not archives:
                print("Error: No archive found. Please specify archive path.")
                print("Usage: python sync_personal_data.py import <archive.zip>")
                sys.exit(1)
            archive_path = max(archives, key=lambda p: p.stat().st_mtime)
            print(f"Using most recent archive: {archive_path}")
    
    archive_path = Path(archive_path)
    if not archive_path.exists():
        print(f"Error: Archive not found: {archive_path}")
        sys.exit(1)
    
    print(f"Extracting {archive_path}...")
    
    with zipfile.ZipFile(archive_path, 'r') as zipf:
        zipf.extractall(".")
    
    print("[+] Import complete")
    print("\nImported directories:")
    for dir_path in PRIVATE_DIRS:
        path = Path(dir_path)
        if path.exists():
            if path.is_file():
                print(f"  {dir_path} (file)")
            else:
                file_count = len(list(path.rglob("*")))
                print(f"  {dir_path}/ ({file_count} items)")
    
    if HAS_GUI:
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Import Complete", "Private data imported successfully!\n\nYou can now run chaits.py")
        root.destroy()

def show_gui_menu():
    """Show GUI menu when no command provided"""
    if not HAS_GUI:
        return None
    
    root = tk.Tk()
    root.title("chaits Data Sync Tool")
    root.geometry("400x250")
    root.resizable(False, False)
    
    result = {"action": None}
    
    def on_export():
        result["action"] = "export"
        root.destroy()
    
    def on_import():
        result["action"] = "import"
        root.destroy()
    
    def on_list():
        result["action"] = "list"
        root.destroy()
    
    # Title
    tk.Label(root, text="chaits Personal Data Sync", 
             font=("Arial", 14, "bold")).pack(pady=20)
    
    tk.Label(root, text="What would you like to do?", 
             font=("Arial", 10)).pack(pady=10)
    
    # Buttons
    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=20)
    
    tk.Button(btn_frame, text="📦 Export Data", width=20, height=2,
              command=on_export, font=("Arial", 10)).pack(pady=5)
    tk.Button(btn_frame, text="📥 Import Data", width=20, height=2,
              command=on_import, font=("Arial", 10)).pack(pady=5)
    tk.Button(btn_frame, text="📋 List Files", width=20, height=2,
              command=on_list, font=("Arial", 10)).pack(pady=5)
    
    root.mainloop()
    return result["action"]

def main():
    # If no arguments provided, try GUI menu
    if len(sys.argv) < 2:
        if HAS_GUI:
            command = show_gui_menu()
            if command is None:
                print("Cancelled")
                return
        else:
            print(__doc__)
            sys.exit(1)
    else:
        command = sys.argv[1].lower()
    
    if command == "list":
        list_private_data()
    elif command == "export":
        output = sys.argv[2] if len(sys.argv) > 2 else None
        export_private_data(output)
    elif command == "import":
        archive = sys.argv[2] if len(sys.argv) > 2 else None
        import_private_data(archive)
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()
