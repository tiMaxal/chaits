# chaits

**Cross-AI Chat Index & Discovery Tool**

Local, offline desktop app for indexing, searching, and semantically correlating conversations across multiple AI services.

AI-voding [vibe-coding] in VS-Code with Copilot by tiMaxal.
 .. this is directed AI code creation, not written by a competent coder; all care possible has been taken, but no responsibility accepted for use by others!

## Why chaits?

Personal knowledge management and research continuity across AI providers. Search your entire AI conversation history from one place — keyword search, semantic search, or both.

## Supported Services

ChatGPT • Claude • Gemini • Grok • GitHub Copilot (VS-Code)

## Key Features

- **Hybrid Search**: Keyword (SQLite FTS5) + Semantic (embeddings) with intelligent ranking
- **Multi-Account Support**: Index conversations from multiple accounts per service
- **Timeline Tracking**: VS Code extension for accurate per-message timestamps
- **Cross-Service Discovery**: Find related conversations across different AI providers
- **Privacy First**: Fully offline, no network calls, all data stays local
- **Export Tools**: CSV exports compatible with LibreOffice/Excel/OnlyOffice

## Quick Start

```bash
# Install dependencies
pip install sentence-transformers numpy

# Launch GUI
python chaits.py
```

## Directory Structure

Place exported JSON files in:
```
.aiccounts/accounts_{service}/{account}/exports/*.json
```

Example:
```
.aiccounts/
├── accounts_chatgpt/timax/exports/conversations.json
├── accounts_claude/user@email.com/exports/claude_chats.json
└── accounts_copilot/timax/exports/vscode_copilot_*.json
```

## Exporting Conversations

### VS Code Copilot

**Workspace Export** (numbered markdown files):
```bash
python export_workspace_chats.py  # GUI mode with multi-select
```

**Database Export** (JSON for indexing):
```bash
python export_vscode_copilot.py  # GUI or --cli mode
```

### Other Services

- **ChatGPT**: Settings → Data controls → Export data
- **Claude**: Export from web interface
- **Grok**: Browser developer tools → Export API responses
- **Gemini**: Google Takeout

## Enhanced Timeline Tracking

Install the **chaits-tracker VS Code extension** for accurate per-message timestamps:

- Auto-install: Run `python chaits.py` (one-click prompt)
- Manual: See `chaits-tracker-extension/INSTALL.md`

**Why?** VS Code only tracks conversation start times, not individual message timestamps. This extension records exact timing for every interaction across all workspaces.

## Usage

1. Export conversations from your AI services
2. Place JSON files in `.aiccounts/accounts_{service}/{account}/exports/`
3. Run `python chaits.py`
4. Search using keyword, semantic, or hybrid modes
5. Export results to CSV for external analysis

## Security & Privacy

- ✓ Fully offline operation
- ✓ No credentials stored
- ✓ No network calls
- ✓ Hash-based deduplication
- ✓ Optional read-only audit mode

## Documentation

- `chaits.README.md` - Complete documentation
- `EXTENSION_INTEGRATION.md` - Timeline tracking details
- `chaits-tracker-extension/QUICKSTART.md` - Extension setup guide

## License

Created for personal knowledge management and research continuity.
