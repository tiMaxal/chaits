# Chaits Tracker - VS Code Extension

**Accurate per-message timestamp tracking for GitHub Copilot chats across all workspaces**

## The Problem This Solves

VS Code only stores session creation timestamps for Copilot chats - not when individual messages were sent. When you switch between multiple projects during development, it's impossible to reconstruct an accurate timeline of your work later.

**Chaits Tracker** captures the exact timestamp of every chat interaction, enabling you to:

- Track when you actually used Copilot, not just when you started a conversation
- Correlate chat activity with Git commits and file edits
- Reconstruct accurate project progression timelines
- Analyze development patterns across multiple workspaces

## Features

### Core Functionality

- **Per-message timestamps** - Records exact time of every user/assistant interaction
- **Cross-workspace tracking** - Unified timeline across all your projects
- **Cross-chat correlation** - Tracks activity as you switch between chat sessions within a workspace
- **Global storage** - Data syncs via Settings Sync to all your machines
- **Privacy controls** - Optionally store timestamps without message content

### Correlation Features

- **Git integration** - Links chat activity with commit timestamps
- **File edit tracking** - Correlates chat with file modifications
- **Workspace context** - Preserves which project each chat belongs to

### Export & Analysis

- **Chaits-compatible format** - Direct integration with chaits timeline tool
- **Auto-export** - Optional daily exports to `.aiccounts` directory
- **Manual export** - On-demand export with custom paths

### User Interface

- **Activity Bar view** - Quick access to timeline and settings
- **Status bar indicator** - Shows tracking is active
- **Timeline viewer** - Browse recent interactions in VS Code
- **Settings GUI** - User-friendly configuration panel

## Installation

### Option 1: Auto-Install via chaits (Easiest)

**Let chaits handle everything:**

```bash
python chaits.py
```

On first launch, chaits will:
- Detect the extension isn't installed
- Offer one-click installation
- Auto-build the extension (requires Node.js)
- Auto-install using VS Code CLI
- Show success confirmation

**Requirements:** Node.js installed. If missing, chaits prompts to download.

---

### Option 2: Manual Build & Install

**Prerequisites:** Node.js installed (download from nodejs.org)

```bash
cd chaits-tracker-extension
npm install          # Install dependencies
npm run compile      # Build TypeScript
npm run package      # Create .vsix package
code --install-extension chaits-tracker-0.1.0.vsix  # Install
```

**Why build from source?**

- Optimized for your system
- Always latest version
- No platform compatibility issues
- Standard practice for dev tools

**Detailed walkthrough:** See [INSTALL.md](INSTALL.md) for step-by-step guide

### Settings Sync

Once installed on one machine, enable Settings Sync to auto-deploy to all your devices:

- Go to: `Settings` → `Settings Sync` → Turn on
- The extension settings and installation will sync automatically

## Configuration

All settings sync across machines via VS Code Settings Sync.

### Essential Settings

**Enable/Disable Tracking**

```json
"chaits.tracking.enabled": true
```

**Storage Location** (global = syncs everywhere)

```json
"chaits.tracking.storage": "global"
```

**Privacy Mode** (timestamps only, no content)

```json
"chaits.tracking.includeContent": false
```

### Advanced Settings

**Git Correlation**

```json
"chaits.correlate.gitCommits": true,
"chaits.correlate.fileEdits": true
```

**Auto Export** (daily export to chaits format)

```json
"chaits.export.autoExport": true,
"chaits.export.path": "E:/STORE/DOCS/text/code_text/_vode_ai-assist/ai_chaits/.aiccounts/accounts_copilot/exports"
```

**Exclude Workspaces** (skip tracking for specific projects)

```json
"chaits.privacy.excludeWorkspaces": ["sensitive-client-project", "personal-diary"]
```

## Usage

### Viewing Timeline

- Click **Chaits Tracker** icon in Activity Bar
- Or: `Ctrl+Shift+P` → `Chaits: View Chat Timeline`

### Exporting Data

- `Ctrl+Shift+P` → `Chaits: Export Timestamp Data`
- Data exports to `.aiccounts/accounts_copilot/exports/` by default
- Compatible with chaits main application

### Checking Status

- Click status bar clock icon (minimal by default)
- Or: `Ctrl+Shift+P` → `Chaits: Show Tracking Status`

## Integration with Chaits

This extension exports data in chaits-compatible format. To analyze your timeline:

1. **Export from extension** (or set auto-export)
2. **Open chaits** (`python chaits.py`)
3. **Click 🔄 Refresh** - New data auto-imports
4. **Search/analyze** - Full timeline correlation across services

### Export Format

```json
{
  "export_source": "chaits-tracker-extension",
  "export_timestamp": 1738022400000,
  "version": "1.0",
  "conversations": [
    {
      "conversation_id": "uuid-here",
      "conversation_title": "Brief chat summary...",
      "create_time": 1738000000,
      "workspace": "ai_chaits",
      "messages": [
        {
          "role": "user",
          "content": "How do I implement X?",
          "timestamp": 1738000100000
        },
        {
          "role": "assistant",
          "content": "You can implement X by...",
          "timestamp": 1738000105000
        }
      ]
    }
  ]
}
```

## Data Storage

**Location**: `%APPDATA%/Code/User/globalStorage/chaits-tracker/`

**Structure**:

```
interaction-logs/
  ├── interactions-2026-01-22.jsonl    # Daily logs
  ├── interactions-2026-01-23.jsonl
  ├── session-<uuid>.jsonl             # Per-session logs
  ├── session-<uuid>.json              # Session metadata
  └── file-edits.jsonl                 # File edit correlation
```

**Size**: ~1KB per conversation, ~10MB per year of active use

**Privacy**: Local-only storage, no network transmission

## Privacy & Security

- [+] **Local processing only** - No data sent to external servers
- [+] **Optional content exclusion** - Can store timestamps without messages
- [+] **Workspace exclusion** - Skip tracking for sensitive projects
- [+] **User control** - Easy disable/enable without uninstalling
- [+] **Standard VS Code storage** - Uses official globalStorage APIs

### Disabling Tracking

```json
"chaits.tracking.enabled": false
```

Or uninstall: `code --uninstall-extension chaits-tracker`

## Troubleshooting

### Extension Not Tracking

1. Check status: `Chaits: Show Tracking Status`
2. Verify enabled: `Settings` → search `chaits.tracking.enabled`
3. Restart VS Code
4. Check output: `View` → `Output` → `Chaits Tracker`

### Data Not Exporting

1. Verify export path exists
2. Check permissions on target directory
3. Try manual export: `Chaits: Export Timestamp Data`

### Timeline Shows No Data

1. Ensure you've had Copilot conversations since installing
2. Check storage directory exists: `%APPDATA%/Code/User/globalStorage/chaits-tracker/`
3. Verify files are being created during chats

## Contributing

This extension is part of the [chaits project](https://github.com/yourusername/chaits).

### Development Setup

```bash
git clone https://github.com/yourusername/chaits.git
cd chaits/chaits-tracker-extension
npm install
code .
# Press F5 to launch extension development host
```

### Building

```bash
npm run compile        # TypeScript → JavaScript
npm run package        # Create .vsix
npm run install-local  # Install locally
```

## Requirements

- **VS Code**: 1.85.0 or later
- **GitHub Copilot**: Installed and active
- **Disk Space**: ~50MB for storage
- **Node.js**: 20.x or later (for development only)

## Roadmap

- [ ] Real-time Git commit correlation
- [ ] Multi-participant chat support
- [ ] Custom export formats (CSV, SQLite)
- [ ] Timeline visualization in extension
- [ ] Code context correlation (which files were discussed)
- [ ] Workspace-level analytics dashboard

## License

Same as chaits main project (specify your license)

## Support

Issues: <https://github.com/yourusername/chaits/issues>
Docs: <https://github.com/yourusername/chaits/wiki>
