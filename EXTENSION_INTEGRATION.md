# chaits-tracker Extension Integration

## Summary of Changes

This document describes the integration of the `chaits-tracker` VS Code extension with the chaits main application, enabling accurate per-message timestamp tracking across all Copilot chat interactions.

---

## Problem Solved

**Issue**: VS Code only stores session creation timestamps for Copilot chats, not individual message timestamps. When developers switch between multiple projects during work sessions, it's impossible to reconstruct accurate timelines later.

**Solution**: The `chaits-tracker` extension captures exact timestamps for every user-assistant interaction in real-time, enabling:
- Accurate timeline reconstruction across workspace switches
- Correlation with Git commits and file edits
- Understanding when development work actually occurred
- Multi-project workflow tracking

---

## Components Created

### 1. VS Code Extension (`chaits-tracker-extension/`)

**Core Files**:
- `src/extension.ts` - Entry point with welcome GUI
- `src/timestampTracker.ts` - Real-time chat monitoring and logging
- `src/exportManager.ts` - Chaits-compatible data export
- `src/settingsProvider.ts` - Settings UI tree view
- `src/timelineProvider.ts` - Timeline visualization

**Features**:
- ✅ Monitors VS Code workspace storage for chat activity
- ✅ Logs per-message timestamps to global storage
- ✅ Exports in chaits-compatible JSON format
- ✅ Syncs via VS Code Settings Sync to all machines
- ✅ Optional privacy mode (timestamps only, no content)
- ✅ Git and file edit correlation
- ✅ Activity bar view with timeline browser
- ✅ Status bar indicator

**Storage Location**:
```
%APPDATA%/Code/User/globalStorage/chaits-tracker/interaction-logs/
  ├── interactions-2026-01-22.jsonl    # Daily logs
  ├── session-<uuid>.jsonl             # Per-session logs
  └── file-edits.jsonl                 # File edit correlation
```

**Documentation**:
- `README.md` - Feature documentation
- `INSTALL.md` - Step-by-step installation for non-technical users
- `QUICKSTART.md` - 5-minute setup guide
- `BUILD.md` - Development and build instructions

### 2. Integration with Existing Tools

#### A. `export_vscode_copilot.py`

**Changes**:
- Added `load_extension_timestamps()` function
- Gracefully handles missing extension (returns empty dict)
- Merges extension timestamps with VS Code session data
- Marks enhanced conversations with `has_per_message_timestamps` flag
- Shows `[time-tracked]` indicator for enhanced data

**Example Output**:
```
++ Loading timestamps from chaits-tracker extension...
  + Loaded 45 timestamped messages for session abc12345
  ++ Total: 12 sessions with enhanced timestamps
  + Extracted: Fix database bug (15 messages) [time-tracked]
```

#### B. `export_workspace_chats.0-2-0.py`

**Changes**:
- Added `load_extension_timestamps()` function (cross-platform)
- Integrates extension data when exporting workspace chats
- Adds per-message timestamps to markdown exports
- Preserves `has_per_message_timestamps` metadata

#### C. `chaits.0-5-0.py` (Main Application)

**New Functions**:
- `is_extension_installed()` - Detects extension installation
- `get_prompt_status()` / `set_prompt_status()` - Tracks user prompt choices
- `check_extension_prompt()` - Triggered 500ms after startup
- `show_extension_install_dialog()` - User-friendly install prompt
- `install_extension_dialog()` - Installation instructions with auto-install

**User Experience**:
1. Chaits starts up
2. If extension not installed and not previously dismissed:
   - Shows friendly dialog explaining benefits
   - Options: "Install Extension" / "Remind Me Later" / "Don't Ask Again"
3. If user clicks "Install Extension":
   - Shows installation instructions
   - Auto-detects if `.vsix` exists
   - Offers "Install Now" button (runs `code --install-extension`)
   - Fallback to manual instructions if needed

**Prompt Persistence**:
- Status saved in: `db/.extension_prompt_status`
- Values: `never` / `later` / `ignored` / `installed`
- Won't re-prompt if user chose "Don't Ask Again"

---

## Data Flow

### Without Extension (Current Behavior)
```
VS Code → chatSessions/*.json → export_vscode_copilot.py → chaits
                                  (session-level timestamps only)
```

### With Extension (Enhanced)
```
VS Code Chat Interaction
    ↓
Extension watches file changes
    ↓
Logs to globalStorage/chaits-tracker/
    ↓
export_vscode_copilot.py merges data
    ↓
chaits imports with per-message timestamps
```

### Export Format Enhancement

**Before**:
```json
{
  "conversation_id": "uuid",
  "conversation_title": "Debug session",
  "create_time": 1738022400,
  "messages": [
    {"role": "user", "content": "How to fix bug?"},
    {"role": "assistant", "content": "Try this..."}
  ]
}
```

**After (with extension)**:
```json
{
  "conversation_id": "uuid",
  "conversation_title": "Debug session",
  "create_time": 1738022400,
  "has_per_message_timestamps": true,
  "messages": [
    {
      "role": "user",
      "content": "How to fix bug?",
      "timestamp": 1738022505123
    },
    {
      "role": "assistant",
      "content": "Try this...",
      "timestamp": 1738022510456
    }
  ]
}
```

---

## Installation Workflow

### For End Users

**Method 1: Via Chaits (Recommended)**
1. Run `python chaits.py`
2. Dialog appears: "Accurate Timeline Tracking Available"
3. Click "Install Extension"
4. Follow auto-generated instructions
5. Click "Install Now" (if `.vsix` exists)
6. Restart VS Code

**Method 2: Manual Install**
1. Navigate to `chaits-tracker-extension/`
2. Build: `npm install && npm run package`
3. Install: `code --install-extension chaits-tracker-0.1.0.vsix`
4. Restart VS Code

**Method 3: From VS Code Marketplace (Future)**
- Search for "chaits tracker"
- Click Install

### For Developers

```bash
cd chaits-tracker-extension
npm install
npm run compile
npm run watch  # Auto-recompile on changes
# Press F5 in VS Code to launch Extension Development Host
```

---

## Configuration

### Extension Settings (Syncs Across Machines)

**Essential**:
```json
{
  "chaits.tracking.enabled": true,
  "chaits.tracking.storage": "global",
  "chaits.tracking.includeContent": true
}
```

**Privacy Mode**:
```json
{
  "chaits.tracking.includeContent": false,  // Timestamps only
  "chaits.privacy.excludeWorkspaces": ["confidential-client"]
}
```

**Auto-Export**:
```json
{
  "chaits.export.autoExport": true,
  "chaits.export.path": "E:/path/to/.aiccounts/accounts_copilot/exports"
}
```

### Chaits Main App Settings

No configuration needed - extension data is automatically detected and merged during export.

---

## Backward Compatibility

**100% backward compatible**:
- [+] All existing functionality works without extension
- [+] Export tools gracefully handle missing extension data
- [+] No errors if extension not installed
- [+] Existing data formats unchanged
- [+] Extension data is additive only

**Graceful Degradation**:
```python
# Both export tools use this pattern:
extension_timestamps = load_extension_timestamps()  # Returns {} if not found

# Later:
if session_id in extension_timestamps:
    # Use enhanced timestamps
else:
    # Fall back to session-level timestamp
```

---

## Use Cases

### 1. Multi-Project Timeline Reconstruction

**Scenario**: Developer works on 3 projects in one day, switching frequently.

**Without Extension**:
- 3 chat sessions with start times only
- Can't determine when individual questions were asked
- Timeline is ambiguous

**With Extension**:
- Exact timestamp for every interaction
- Can see: "Asked about DB at 2:15 PM in Project A, then switched to API question in Project B at 2:45 PM"
- Accurate reconstruction months later

### 2. Development Velocity Analysis

**Questions Answered**:
- How long between asking and implementing?
- Which projects consume most assistance time?
- When do you typically need help? (time of day patterns)

### 3. Onboarding Documentation

**Use Case**: New team member asks, "How was this feature developed?"

**With Extension**:
- Export timeline showing exact conversation sequence
- Correlate with Git commits: "Asked about auth at 3 PM, committed fix at 4 PM"
- Comprehensive development narrative

---

## Privacy & Security

### Extension
- [+] **Local-only processing** - No external network calls
- [+] **Optional content exclusion** - Store timestamps without messages
- [+] **Workspace exclusion** - Skip tracking for sensitive projects
- [+] **User control** - Easy disable/enable without uninstall
- [+] **Standard VS Code APIs** - Uses official globalStorage

### Chaits Integration
- [+] **No additional data collection** - Only reads existing files
- [+] **Opt-in** - Extension install is entirely optional
- [+] **Transparent** - Shows what data is enhanced with `[time-tracked]` marker

---

## Testing

### Extension
1. Install extension
2. Have Copilot conversation
3. Check: `%APPDATA%/Code/User/globalStorage/chaits-tracker/interaction-logs/`
4. Verify `.jsonl` files created
5. Run: `Chaits: View Chat Timeline`
6. Export: `Chaits: Export Timestamp Data`

### Integration
1. Run `python export_vscode_copilot.py`
2. Look for: "++ Loading timestamps from chaits-tracker extension..."
3. Check output shows: `[time-tracked]` for enhanced conversations
4. Verify exported JSON has `timestamp` fields in messages
5. Open chaits, refresh, confirm data imported

---

## Troubleshooting

### Extension Not Tracking

**Check**:
1. Status bar shows `[Chaits]`
2. Settings: `chaits.tracking.enabled` is `true`
3. Storage directory exists and writable
4. Have had Copilot conversations since installing

**Fix**: `Developer: Reload Window`

### Export Tools Not Finding Extension Data

**Check**:
1. Extension installed and active?
2. Storage path correct for your OS?
3. `.jsonl` files exist in storage directory?

**Fix**: Data merging is optional - exports work regardless

### Chaits Not Prompting

**Check**:
1. `db/.extension_prompt_status` - may be set to `ignored`
2. Extension already installed (won't prompt)

**Fix**: Delete `db/.extension_prompt_status` to reset

---

## Future Enhancements

### Short-Term
- [ ] Real-time Git commit correlation
- [ ] Code context tracking (which files discussed)
- [ ] Timeline visualization in extension webview

### Long-Term
- [ ] Publish to VS Code Marketplace
- [ ] Support for other AI chat extensions
- [ ] Multi-user workspace analytics
- [ ] Integration with project management tools

---

## Files Modified/Created

### New Files
```
chaits-tracker-extension/
  ├── src/*.ts (5 files)
  ├── package.json
  ├── tsconfig.json
  ├── README.md
  ├── INSTALL.md
  ├── QUICKSTART.md
  └── BUILD.md
```

### Modified Files
```
export_vscode_copilot.py       - Added extension timestamp loading
export_workspace_chats.0-2-0.py - Added extension timestamp loading
chaits.0-5-0.py                - Added extension detection & install prompt
```

### Configuration Files
```
db/.extension_prompt_status    - Tracks user prompt preferences (auto-created)
```

---

## Summary

The `chaits-tracker` extension + integration provides:

[+] **Accurate timestamps** for every Copilot interaction  
[+] **Cross-workspace & cross-chat tracking** unified in one location
[+] Time-correlates activity as you switch between different chats in a workspace  
[+] **Automatic sync** to all machines via Settings Sync  
[+] **User-friendly setup** with GUI prompts and auto-install  
[+] **Backward compatible** - existing workflows unaffected  
[+] **Privacy-focused** - local-only, optional content exclusion  
[+] **Seamless integration** - chaits auto-detects enhanced data  

**Result**: Complete, accurate development timeline reconstruction enabling deep insights into project progression and work patterns.
