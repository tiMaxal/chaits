
# chaits

## **Cross-AI Chat Index & Discovery Tool**

`chaits` is a **local, offline desktop application** for indexing, searching, and semantically correlating conversations across multiple AI services and multiple accounts.

AI-voding [vibe-coding] in VS-Code with Copilot by tiMaxal.
 .. this is directed AI code creation, not written by a competent coder; all care possible has been taken, but no responsibility accepted for use by others!

### Intended Use

Personal knowledge management, research continuity, and long-term AI conversation archiving across providers.

#### chaits does not merge, modify, or rewrite conversation history

## Supported Services

- ChatGPT
- Claude  
- Gemini
- Grok
- GitHub Copilot (VS-Code)

## Enhanced Timeline Tracking

### chaits-tracker VS-Code Extension

For accurate per-message timestamp tracking across all Copilot conversations:

**Why You Need This:**

- VS-Code only stores *when conversations start*, not when individual messages were sent
- Switching between workspaces destroys timeline chronology
- Impossible to reconstruct accurate development timelines later

**What It Does:**

- [+] Records exact timestamp for every Copilot interaction
- [+] Tracks across all workspaces in unified storage
- [+] Syncs to all your machines via Settings Sync
- [+] Exports in chaits-compatible format
- [+] Optional: Git commit & file edit correlation
- [+] Privacy mode: timestamps only, no content

**Installation:**

1. **Auto-install (easiest):** Run `python chaits.py` - One-click installation prompt on first launch
   - Automatically builds and installs the extension
   - Requires Node.js (prompts if missing)
   - Handles all build steps for you

2. **Manual build:**
   ```bash
   cd chaits-tracker-extension
   npm install && npm run compile && npm run package
   code --install-extension chaits-tracker-0.1.0.vsix
   ```

**Documentation:**

- `chaits-tracker-extension/INSTALL.md` - Step-by-step guide for beginners
- `chaits-tracker-extension/QUICKSTART.md` - 5-minute setup
- `chaits-tracker-extension/BUILD.md` - Build process details
- `EXTENSION_INTEGRATION.md` - Technical overview

**Usage:**

- Extension tracks automatically once installed
- Minimal status bar indicator (icon-only by default)
- Export tools automatically detect and merge enhanced timestamp data
- Look for `[time-tracked]` marker in exports

**Result:** Accurate timeline reconstruction showing *exactly* when you asked what, across all projects.

## Features

### Search & Discovery

- **Keyword search** (SQLite FTS5)
- **Semantic search** (SentenceTransformers embeddings)
- **Hybrid ranking** (60% keyword + 40% semantic)
- **Sortable results** (click column headers)
- Timeline view per conversation

### Organization

- **Conversation browser** with service filtering
- Multi-account isolation
- Cross-account semantic linking
- Find follow-up conversations across services
- Tagging & pinning (planned)

### Export

- **CSV export** with cell splitting for LibreOffice/Excel/OnlyOffice compatibility
- Export current search results (filtered view)
- Export all services chronologically
- Export by individual service
- Conversation sequence preservation

### Security & Privacy

- **Fully offline** and local
- No network calls
- No credentials stored
- All data stored locally
- **Read-only audit mode** option
- Secure, read-only correlation

## Installation

```bash
pip install sentence-transformers numpy
```

## Quick Start

```bash
python chaits.py  # Launch GUI
```

## Directory Layout

```
.aiccounts/accounts_{service}/{account}/exports/*.json
├── .aiccounts/
│   ├── accounts_chatgpt/
│   ├── accounts_claude/
│   ├── accounts_copilot/
│   ├── accounts_gemini/
│   └── accounts_grok/
```

## Exporting Conversations

### VS-Code Copilot

#### Workspace-Specific Export (Recommended)

Export chats as **numbered markdown files** directly into workspace directories to preserve them when renaming workspaces:

```bash
python export_workspace_chats.py                      # GUI mode - pick workspace(s)
python export_workspace_chats.py --list               # List all workspaces
python export_workspace_chats.py --current            # Export current workspace
python export_workspace_chats.py --workspace "path"   # Export specific workspace
```

**Features:**

- **Chronological numbering**: Files saved as `001_chat_title.md`, `002_another_chat.md`, etc.
- **Multi-select**: Export multiple workspaces at once (Select All/None buttons)
- **Conflict handling**: Choose to overwrite, add suffix, or skip existing files
- **Column sorting**: Click Name/Path/Chats headers to sort workspace list
- **Search filter**: Narrow workspace selection by name or path
- **Default location**: `{workspace}/.vscode/copilot_history/`
- **Recursive extraction**: Advanced parsing for complex response formats
- **Debug mode**: Save unparseable responses for troubleshooting

Exported markdown files stay with the workspace even when directory is renamed, preventing loss of chat history.

#### Legacy JSON Export

For indexing in chaits database (with optional enhanced timestamps from extension):

```bash
python export_vscode_copilot.py  # GUI mode
python export_vscode_copilot.py --cli  # CLI mode
```

**If chaits-tracker extension is installed:**

- Automatically merges per-message timestamps
- Shows `[time-tracked]` for conversations with enhanced data
- No configuration needed - works automatically

### Other Services

Manually export conversations from:

- ChatGPT: Settings → Data controls → Export data
- Claude: Export from web interface
- Grok: Use browser developer tools to export API responses
- Gemini: Google Takeout

Place JSON files in `{service}_accounts/{account}/exports/` and click 🔄 Refresh.

## Usage

1. **Search**: Enter query and click Keyword/Semantic/Hybrid
2. **Browse**: Click 💬 Conversations to explore by service
3. **Sort**: Click any column header to sort results
4. **View**: Double-click conversation to view full history
5. **Export**: Click Export for CSV downloads
   - Export Search Results: Save current filtered view
   - Export All Services: Complete chronological archive
   - Export by Service: Individual service data

## Technical Details

- **Embedding Model**: all-MiniLM-L6-v2 (384 dimensions)
- **Database**: SQLite with FTS5 and custom cosine similarity
- **Cell Limit**: 32,000 characters (Excel/LibreOffice/OnlyOffice compatible)
- **Lazy Loading**: Embedding model loads on first use

## Security Model

- No data modification
- Hash-based deduplication
- Audit mode disables all writes
- Correlation is semantic only
