# Setup Guide for New Machines

Quick guide to set up chaits on a new machine with your existing data.

## Initial Setup (New Machine)

### 1. Clone the Repository

```bash
git clone <your-repo-url> ai_chaits
cd ai_chaits
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Import Your Private Data

**Option A: Using sync tool with GUI (recommended)**

```bash
python sync_personal_data.py import
# Opens file picker to select your chaits_private_data_YYYYMMDD_HHMMSS.zip
```

**Option B: Using sync tool with CLI**

```bash
# Copy your chaits_private_data_YYYYMMDD_HHMMSS.zip to this directory
python sync_personal_data.py import chaits_private_data_YYYYMMDD_HHMMSS.zip
```

**Option C: Manual setup**

```bash
# Copy your backed-up data to:
# - .aiccounts/ (your chat exports)
# - db/ (your database files)
# - chaits_exports/ (your CSV exports, if any)
```

### 4. Verify Setup

```bash
python chaits.py
```

The app should launch with all your conversations indexed and searchable.

## Adding New Conversations

1. Export conversations from your AI services:
   - **ChatGPT**: Settings → Data controls → Export data
   - **Claude**: Settings → Export data
   - **Gemini**: Export from chat interface
   - **Grok**: Use browser dev tools to capture API responses
   - **GitHub Copilot**: Run `python export_vscode_copilot.py`

2. Place exported JSON files in:

   ```
   .aiccounts/accounts_{service}/{account_name}/exports/
   ```

3. Refresh in the app (🔄 button) or restart chaits

## Syncing Changes Back

When you want to sync your updated data to another machine:

**GUI Mode (recommended):**

```bash
python sync_personal_data.py export
# Opens save dialog to choose location
```

**CLI Mode:**

```bash
python sync_personal_data.py export /path/to/backup/chaits_backup.zip
# Or just: python sync_personal_data.py export
# Creates: chaits_private_data_YYYYMMDD_HHMMSS.zip in current directory
```

Transfer this ZIP file to your other machine and import it there.

## Directory Structure

After import, you should have:

```
ai_chaits/
├── .aiccounts/            # Your private chat exports (files gitignored)
│   ├── accounts_chatgpt/
│   ├── accounts_claude/
│   ├── accounts_copilot/
│   ├── accounts_gemini/
│   └── accounts_grok/
├── db/                    # Your indexed database (gitignored)
│   └── chaits.sqlite
├── chaits_exports/        # Your CSV exports (gitignored)
├── chaits.py              # Main application
└── sync_personal_data.py  # Data management tool
```

## Troubleshooting

### "No conversations found"

- Check that `.aiccounts/` exists and contains your data
- Verify JSON files are in the correct directory structure
- Check file permissions

### "Database is empty"

- Delete `db/chaits.sqlite`
- Restart chaits to re-index from JSON files

### "Import failed"

- Verify the ZIP file is not corrupted
- Check available disk space
- Try manual extraction: `unzip -l chaits_private_data_*.zip`

### GUI doesn't appear for sync tool

- GUI requires tkinter (usually included with Python)
- Use CLI mode as fallback: `python sync_personal_data.py export output.zip`

## Privacy Reminder

**Never commit:**

- `.aiccounts/**/*.json` - Contains your private conversations
- `db/*.sqlite` - Contains indexed conversation data
- `chaits_exports/*.csv` - May contain conversation excerpts
- `chaits_private_data_*.zip` - Backup archives

These are protected by `.gitignore`, but always verify before pushing:

```bash
git status  # Should not show any of the above
```
