# Quick Start Guide - Chaits Tracker Setup

## For New Users

**Goal**: Get accurate per-message timestamps for all Copilot chats across every workspace.

**Time needed**: 10 minutes

---

## Installation Path

### Option A: Complete First-Time Setup

**1. Install Extension** → **2. Configure (optional)** → **3. Use normally**

### Option B: Already Have Chaits

**1. Install Extension** → **2. Done** (Auto-exports to your existing setup)

---

## Step 1: Install Extension

### Download & Install
```bash
# If you have the .vsix file:
code --install-extension chaits-tracker-0.1.0.vsix

# Or manually:
# 1. Open VS Code
# 2. Extensions view (Ctrl+Shift+X)
# 3. Click ⋯ → Install from VSIX
# 4. Select chaits-tracker-0.1.0.vsix
```

### Verify Installation
Look for a small **clock icon** ($(history)) in bottom-right status bar.

[+] See it? → Extension is working!  
[-] Don't see it? → Restart VS Code

**Note:** Status bar is minimal by default (icon-only). You can change this in settings if needed.

---

## Step 2: First Run

### Welcome Screen
On first launch, you'll see a welcome screen explaining:
- What the extension does
- What data is collected
- Where it's stored

**Two options:**
- **Configure Settings** - Customize behavior
- **Start Using** - Use default settings (recommended)

### Default Behavior (No Config Needed!)

[+] **Tracking enabled** - Records all chats  
[+] **Global storage** - Syncs across machines  
[+] **Full content** - Saves messages for analysis  
[+] **Git correlation** - Links with commits  
[+] **Auto-export** - Disabled (manual export)  

**You can start using Copilot immediately - no setup required.**

---

## Step 3: Sync to Other Machines (Optional)

### Enable Settings Sync (One-Time)
1. `File → Preferences → Settings Sync`
2. Click **"Turn On Settings Sync"**
3. Sign in with GitHub/Microsoft account
4. Ensure **"Extensions"** is checked
5. Click **"Turn On"**

### On Other Computers
1. Open VS Code
2. Sign in with same account
3. Wait 2 minutes
4. Extension auto-installs! [+]

---

## Verification

### Check It's Working

**Method 1: Status Bar**
- Click the clock icon in status bar (bottom-right)
- See stats: interactions tracked, sessions, etc.

**Method 2: Timeline View**
1. Press `Ctrl+Shift+P`
2. Type: `chaits timeline`
3. See your recent chats with exact timestamps

**Method 3: Check Storage**
Navigate to:
```
%APPDATA%/Code/User/globalStorage/chaits-tracker/interaction-logs/
```
You should see `.jsonl` files being created.

---

## Integration with Chaits Main App

### If You Already Have Chaits

**Automatic integration:**
1. Extension exports to: `.aiccounts/accounts_copilot/exports/`
2. Chaits auto-detects new files on refresh
3. Per-message timestamps preserved

**Manual export:**
```
Ctrl+Shift+P → Chaits: Export Timestamp Data
```

### If You Don't Have Chaits Yet

**Install chaits (the main app):**
```bash
cd ai_chaits
pip install -r requirements.txt
python chaits.py
```

**The extension works standalone**, but chaits provides:
- Cross-service timeline analysis
- Semantic search across all chats
- Project progression tracking
- Git correlation visualization

---

## Common Configurations

### Privacy Mode (Timestamps Only)

**Use case**: Company policy, sensitive code

**Settings:**
```json
{
  "chaits.tracking.includeContent": false
}
```

**Result**: Stores only timestamps + metadata, no message content.

---

### Custom Export Location

**Use case**: Centralized backup folder

**Settings:**
```json
{
  "chaits.export.path": "C:/Users/YourName/Documents/CopilotTimestamps"
}
```

**Result**: All exports go to your custom folder.

---

### Auto-Export Daily

**Use case**: Automated backups without manual action

**Settings:**
```json
{
  "chaits.export.autoExport": true
}
```

**Result**: Exports at midnight daily to chaits format.

---

### Exclude Specific Workspaces

**Use case**: Don't track personal/test projects

**Settings:**
```json
{
  "chaits.privacy.excludeWorkspaces": [
    "my-personal-diary",
    "test-workspace"
  ]
}
```

**Result**: Those workspaces won't be tracked.

---

## Usage Patterns

### Daily Developer Workflow

**Morning:**
- Open VS Code
- Extension auto-starts tracking

**During Work:**
- Use Copilot normally across projects
- Extension silently logs timestamps

**End of Day/Week:**
- (Optional) Export: `Ctrl+Shift+P → Chaits: Export`
- Or: Auto-export handles it

**Later Analysis:**
- Open chaits main app
- See complete timeline of all interactions
- Correlate with Git commits

---

### Multi-Project Switching

**Scenario**: Working on 3 projects simultaneously

**How extension helps:**
1. Tracks which workspace each chat belongs to
2. Records exact time of each interaction
3. Preserves switching context

**Result**: Accurate timeline reconstruction even with frequent project switches.

---

## Troubleshooting

### Extension Not Tracking

**Check:**
1. Status bar shows clock icon (bottom-right corner)? [+]
2. Settings: `chaits.tracking.enabled` is `true`
3. Storage directory exists and is writable

**Fix:**
```
Ctrl+Shift+P → Developer: Reload Window
```

---

### No Timeline Data

**Check:**
1. Have you had Copilot chats since installing?
2. Wait 10 seconds after chat, then check timeline
3. Look in storage folder for `.jsonl` files

**Fix:**
- Have a new Copilot conversation
- Check `View → Output → Chaits Tracker` for errors

---

### Sync Not Working

**Check:**
1. Settings Sync is on (both computers)
2. Same account on both computers
3. Internet connection active

**Fix:**
- `Settings Sync: Show Synced Data`
- Verify extension is in sync manifest
- Manually install on second machine if needed

---

## Next Steps

### You're Ready When:
[+] Extension installed  
[+] Status bar shows `Chaits` (with clock icon)  
[+] Had a test Copilot chat  
[+] Timeline shows the chat  

### Advanced Features to Explore:
- [ ] Enable auto-export
- [ ] Set up Settings Sync (if multi-machine)
- [ ] Configure privacy settings (if needed)
- [ ] Install chaits main app for analysis
- [ ] Set up Git correlation

---

## Getting Help

**Extension issues:**
- `View → Output → Chaits Tracker` (check logs)
- `Chaits: Show Tracking Status` (see what's working)

**Documentation:**
- `README.md` - Full feature documentation
- `INSTALL.md` - Detailed installation guide
- `BUILD.md` - Building from source

**Support:**
- GitHub Issues: [your repo URL]
- Project chat: [if available]

---

## Success Metrics

**You'll know it's working when:**

1. **Status bar** shows active tracking
2. **Timeline view** displays recent chats
3. **Export** creates timestamped JSON files
4. **Storage folder** contains `.jsonl` logs
5. **Chaits app** (if installed) shows the new data

**Congratulations! You now have accurate Copilot timeline tracking.**
