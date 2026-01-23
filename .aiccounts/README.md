# Account Data Directory Structure

This directory contains AI service account data exports.

**Privacy Note:** The directory structure is visible in the repository, but all data files (JSON, CSV, etc.) are excluded via `.gitignore`.

## Directory Structure

```
.aiccounts/
├── accounts_chatgpt/
│   └── {account_name}/
│       └── exports/
│           └── conversations.json  (gitignored)
├── accounts_claude/
│   └── {account_name}/
│       └── exports/
│           └── conversations.json  (gitignored)
├── accounts_copilot/
│   └── {account_name}/
│       └── exports/
│           └── vscode_copilot_*.json  (gitignored)
├── accounts_gemini/
│   └── {account_name}/
│       └── exports/
│           └── conversations.json  (gitignored)
└── accounts_grok/
    └── {account_name}/
        └── exports/
            └── conversations.json  (gitignored)
```

## Setup

1. For each AI service you use, create the directory structure above
2. Export your conversations from each service:
   - **ChatGPT**: Settings → Export data
   - **Claude**: Export from web interface
   - **Gemini**: Export from web interface
   - **Grok**: Use browser dev tools to capture API responses
   - **GitHub Copilot**: Run `python export_vscode_copilot.py`
3. Place the exported JSON files in the appropriate `exports/` directory
4. Launch `python chaits.py` to index and search your conversations

## Privacy

All data files within `.aiccounts/` are excluded from version control via `.gitignore` patterns:
- `**/*.json` - Conversation exports
- `**/*.csv` - CSV exports
- `**/*.txt` - Text files
- `**/*.db` - Database files

Only README.md files and the directory structure itself are tracked by git.
