# Chaits Tracker - Installation Guide

## For Non-Technical Users ("Noobs" 😊)

This guide walks you through installing the extension with zero technical knowledge required.

### What You'll Need

- VS Code installed on your computer
- GitHub Copilot extension (you probably already have this)
- Node.js installed (download from nodejs.org if you don't have it)
- 10 minutes

---

## Step-by-Step Installation

### Option 1: Auto-Install via chaits (Easiest)

**The chaits app can build and install the extension for you automatically!**

**1. Run chaits**
```bash
python chaits.py
```

**2. Installation prompt**
- On first launch, chaits checks if the extension is installed
- If not found, you'll see: **"Enhanced Timeline Tracking Available"** dialog
- Click **"✅ Install Extension"**

**3. Automatic process**
- chaits checks for Node.js/npm (prompts if missing)
- Automatically runs: `npm install`, `npm run compile`, `npm run package`
- Installs the `.vsix` using VS Code CLI
- Shows success confirmation

**4. Restart VS Code**
- Close and reopen VS Code
- Extension starts tracking automatically!

**[+] Done!** Fully automated installation.

**Troubleshooting:**
- If Node.js is missing, chaits will offer to open nodejs.org download page
- If VS Code CLI (`code` command) isn't in PATH, chaits shows manual install instructions
- Click "⏰ Remind Me Later" to skip for now
- Click "🚫 Don't Ask Again" to permanently dismiss the prompt

---

### Option 2: Build & Install from Source (Manual)

**Why build from source?**

- Creates extension optimized for YOUR system
- Always get the latest version
- Avoids platform-specific compatibility issues

**1. Open Terminal/PowerShell**

- In VS Code: Press `Ctrl+Shift+P` → Type "Terminal: Create New Terminal"
- Or use Windows PowerShell/Terminal app

**2. Navigate to extension directory**

```bash
cd chaits-tracker-extension
```

**3. Install dependencies**

```bash
npm install
```

*(Takes ~1-2 minutes - downloads required packages)*

**4. Build the extension**

```bash
npm run compile
npm run package
```

*(Creates `chaits-tracker-0.1.0.vsix` file in current directory)*

**5. Install in VS Code**

```bash
code --install-extension chaits-tracker-0.1.0.vsix
```

*Or manually:*

- Open VS Code Extensions view (`Ctrl+Shift+X`)
- Click **`⋯`** (three dots) → **"Install from VSIX..."**
- Select the newly created `chaits-tracker-0.1.0.vsix`

**6. Reload VS Code** (if prompted)

- Click **"Reload Now"** button
- Or close and reopen VS Code

**[+] Done!** The extension is now tracking your Copilot chats.

---

### Option 2: Install from Marketplace (When Published)

**1. Open Extensions view** (`Ctrl+Shift+X`)

**2. Search** for `"chaits tracker"`

**3. Click "Install"** on the Chaits Tracker extension

**[+] Done!**

---

## First-Time Setup

### Welcome Screen

When you first install, a **welcome screen** will appear. This explains what the extension does.

**Two buttons at the bottom:**

- **Configure Settings** - Click if you want to customize (optional)
- **Start Using** - Click to start with defaults (recommended)

### Default Settings (Already Good!)

The extension works perfectly out-of-the-box with these defaults:

[+] **Tracking enabled** - Recording timestamps automatically  
[+] **Global storage** - Data syncs to all your computers  
[+] **Full content** - Saves messages for later analysis  
[+] **Git correlation** - Links chats with code commits  

**You don't need to change anything unless you want to!**

---

## Verifying It's Working

### Quick Check

**Look for the status icon:**

- Check bottom-right corner of VS Code
- You should see a small clock icon (minimal by default)
- Hover over it to see "Chaits Tracker: Click for status"
- If you see it, everything is working! [+]

**Click the icon** to see stats like:

- How many interactions tracked
- How many chat sessions
- Last export date

---

## Viewing Your Timeline

### Method 1: Activity Bar

1. Look at the left sidebar in VS Code
2. Find the **History icon** (clock symbol)
3. Click it to see:
   - **Chat Timeline** - Your recent conversations
   - **Settings** - Quick status view

### Method 2: Command Palette

1. Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (Mac)
2. Type: `chaits timeline`
3. Select: **"Chaits: View Chat Timeline"**
4. See your conversations with exact timestamps!

---

## Exporting Your Data

### Manual Export

**When you want to export:**

1. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
2. Type: `chaits export`
3. Select: **"Chaits: Export Timestamp Data"**
4. Success message shows where the file was saved
5. Click **"Open Folder"** to see it

### Where Data Goes

**Default location:**

```
Your Workspace/.aiccounts/accounts_copilot/exports/
```

**File format:** `vscode_copilot_tracked_YYYY-MM-DD.json`

**This file is compatible with the main chaits application!**

---

## Syncing Across Computers

Want this on all your machines? Super easy:

### One-Time Setup

1. Open VS Code Settings: `File → Preferences → Settings`
2. Search for: `settings sync`
3. Click: **"Turn On Settings Sync"**
4. Sign in with your GitHub or Microsoft account
5. Make sure **"Extensions"** checkbox is checked
6. Click **"Turn On"**

### On Other Computers

1. Install VS Code (if not already)
2. Open Settings Sync (same steps above)
3. Sign in with the **same account**
4. Wait 2 minutes
5. **Chaits Tracker auto-installs!** [+]

---

## Customizing Settings (Optional)

### Opening Settings

**Easy way:**

1. Click **`🕒 Chaits`** in status bar
2. Click **"Configure"** button

**Or:**

1. Press `Ctrl+,` (Settings)
2. Search: `chaits`
3. See all options

### Important Settings Explained

#### **Privacy Mode** (Hide message content)

```
Setting: "Chaits: Include Content"
Default: [+] On (saves messages)
Change to: [-] Off (saves only timestamps)
```

**When to use:** Working with sensitive company code

#### **Auto Export** (Daily automatic export)

```
Setting: "Chaits: Auto Export"
Default: [-] Off
Change to: [+] On
```

**When to use:** You want daily backups without manual action

#### **Custom Export Path**

```
Setting: "Chaits: Export Path"
Default: (empty - uses workspace)
Change to: Your custom folder path
Example: C:\Users\YourName\Documents\CopilotBackups
```

**When to use:** You want all exports in one place

#### **Status Bar Display**

```
Setting: "Chaits: UI: Status Bar"
Options:
  - icon (default) - Minimal clock icon only
  - text - Show "Chaits" label with icon
  - hidden - No status bar indicator
```

**When to use:** Window real-estate is at a premium (use icon or hidden)

#### **Exclude Workspaces**

```
Setting: "Chaits: Exclude Workspaces"
Default: (empty)
Add: Workspace names to skip
Example: ["client-confidential", "personal-notes"]
```

**When to use:** Some projects shouldn't be tracked

---

## Troubleshooting

### "I don't see the status icon"

**Fix:**

1. Check bottom-right corner carefully
2. Click ⋯ menu in status bar → enable "Chaits"
3. Restart VS Code

### "Extension doesn't show up"

**Fix:**

1. Open Extensions view (`Ctrl+Shift+X`)
2. Search: `@installed chaits`
3. See if it's listed
4. If not, reinstall from .vsix file

### "Timeline is empty"

**Fix:**

1. Make sure you've had Copilot chats since installing
2. Check: `Chaits: Show Tracking Status` command
3. Verify setting: `chaits.tracking.enabled` is `true`
4. Try having a new Copilot chat, then check timeline

### "Export failed"

**Fix:**

1. Make sure the export folder exists
2. Check you have write permissions
3. Try changing export path to your Documents folder
4. Run as administrator (Windows) if needed

### "Data not syncing to other computer"

**Fix:**

1. Verify Settings Sync is on (both computers)
2. Sign in with same account (both computers)
3. Check internet connection
4. Wait 10 minutes, then restart VS Code
5. Manually install on second computer if needed

---

## Uninstalling

**If you want to remove the extension:**

1. Open Extensions view (`Ctrl+Shift+X`)
2. Search: `chaits tracker`
3. Click **"Uninstall"** button
4. Restart VS Code

**Your data is safe!** It stays in:

```
%APPDATA%/Code/User/globalStorage/chaits-tracker/
```

**To fully delete data:**

1. Navigate to the folder above
2. Delete the `chaits-tracker` folder
3. Done

---

## Getting Help

### Check Status First

Run: **"Chaits: Show Tracking Status"** command

- Shows if tracking is working
- Shows how much data collected
- Shows last export

### Read Extension Output

1. Go to: `View → Output`
2. Select: **"Chaits Tracker"** from dropdown
3. See technical logs (for support requests)

### Ask for Help

- **GitHub Issues**: [link to your repo]
- **Discord**: [if you have one]
- **Email**: [your support email]

---

## Tips for Best Results

### [+] Do This

- Keep extension enabled at all times
- Let Settings Sync run in background
- Export data weekly (or enable auto-export)
- Use chaits main app to analyze exports

### [-] Avoid This

- Disabling between sessions (loses timing data)
- Deleting storage folder manually
- Running multiple VS Code instances as different users

---

## Next Steps

**Now that it's installed:**

1. **Use Copilot normally** - Extension tracks automatically
2. **Check timeline occasionally** - See your chat history
3. **Export weekly** - Back up your data
4. **Install chaits main app** - Analyze your timeline

**That's it! You're all set up.**

The extension now tracks every Copilot interaction, giving you accurate timestamps for project timeline reconstruction later.

---

## Quick Reference Card

**Print this and keep at your desk!**

```
╔══════════════════════════════════════════════╗
║        CHAITS TRACKER - QUICK COMMANDS       ║
╠══════════════════════════════════════════════╣
║ View Timeline:    Ctrl+Shift+P → chaits tim ║
║ Export Data:      Ctrl+Shift+P → chaits exp ║
║ Check Status:     Click 🕒 in status bar     ║
║ Open Settings:    Ctrl+, → search "chaits"   ║
║                                              ║
║ Storage Location:                            ║
║ %APPDATA%/Code/User/globalStorage/          ║
║              chaits-tracker/                 ║
║                                              ║
║ Default Export:                              ║
║ .aiccounts/accounts_copilot/exports/         ║
╚══════════════════════════════════════════════╝
```
