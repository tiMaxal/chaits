# Development History - Chaits

AI-voding [vibe-coding] in VS-Code with Copilot by tiMaxal.
 .. this is directed AI code creation, not written by a competent coder; all care possible has been taken, but no responsibility accepted for use by others!

**Cross-AI Chat Index & Discovery Tool**  
Local, offline desktop app for indexing, searching, and semantically correlating conversations across AI services.

---

## December 20, 2025

Initial development session exploring multi-account AI chat aggregation and offline search capabilities. The concept emerged from needing to manage conversations across multiple AI services (ChatGPT, Grok, Claude, Gemini, GitHub Copilot) for different use cases (private, coding, domain management).

**Key Design Decisions**:
- Manual JSON export workflow (no API integration for privacy/security)
- Offline-first architecture with local SQLite storage
- VS Code workspace storage discovery for Copilot chat history
- Original working name: "chaitd" (later evolved)

---

## December 21, 2025 - Initial Development & Refinements

### Version 0-1-0 (370 lines) - Base Implementation
- **Core Architecture**: SQLite database with FTS5 full-text search
- **Embedding System**: Lazy-loaded SentenceTransformer (all-MiniLM-L6-v2) for semantic search
- **Multi-Service Parser**: Initial support for ChatGPT and Grok JSON formats
- **Basic GUI**: Tkinter interface with keyword/semantic/hybrid search
- **Timestamp Handling**: MongoDB extended JSON and Unix timestamp normalization
- **Security**: Hash-based deduplication, no network calls, local-only processing

### Version 0-1-1 (450 lines) - Parser Extensions
- **Enhanced Format Detection**: Improved `parse_generic()` for Copilot conversations array
- **Grok Format**: Full support for `conversations[].{conversation, responses[]}` structure
- **Message Normalization**: Standardized role/content extraction across services
- **Conversation Title**: Fallback handling for untitled conversations

### Version 0-2-0 (536 lines) - Search Refinements
- **Hybrid Search**: 60% keyword BM25 + 40% semantic cosine distance ranking
- **Cross-Account Discovery**: `similar_other_accounts()` for finding related chats across accounts
- **Follow-up Detection**: `followups()` with temporal and semantic similarity filtering
- **Conversation View**: Full conversation display with timestamp and role formatting
- **Manual Refresh**: On-demand indexing trigger (removed auto-polling for resource efficiency)

---

## December 27, 2025 - Feature Development Session

### Version 0-3-0 (875 lines) - CSV Export System
- **Export Functionality**: Dual CSV export implementation
  - All-services chronological export (timestamp-sorted across all AI services)
  - Per-service individual exports (chatgpt, grok, claude, gemini, copilot)
  - Export menu with timestamped filenames: `chaits_all_YYYYMMDD_HHMMSS.csv`
  - 8 columns: Service, Account, Conversation_ID, Conversation_Title, Timestamp_UTC, Timestamp_Raw, Role, Content
- **File Dialog Integration**: `filedialog.asksaveasfilename()` with default extensions and initialfile
- **Database Querying**: Service-filtered and chronological queries with `ORDER BY timestamp_utc ASC`

### Version 0-4-0 (923 lines) - Conversation Browser & Cell Splitting
- **Browse Interface**: Multi-service conversation list with filtering
  - Service checkboxes for all 5 services (All/None quick toggles)
  - `get_conversations()` function with optional service filtering
  - Displays: Service, Account, Title, Message Count, Latest Timestamp
  - Double-click to open full conversation view
  - Sortable column headers (alphabetic for text, numeric for counts, date sorting)
- **CSV Cell Splitting**: Spreadsheet compatibility for large messages
  - `MAX_CELL_CHARS = 32000` (LibreOffice/Excel/OnlyOffice limit: 32767)
  - `split_content_to_rows()` splits messages exceeding limit
  - Role suffixes for split messages (`user_1`, `user_2`, etc.)
  - `add_conversation_sequence_numbers()` adds ` _01`, ` _02` to preserve sort order
- **UI Polish**: Red exit buttons, ESC key bindings, focus management

### Version 0-4-1 (1008 lines) - Import Dialog & How To Guide
- **Import Enhancement**: Replaced text prompts with GUI controls
  - Service: Read-only dropdown with 5 supported services
  - Account: Editable combobox with autocomplete from database
  - `get_existing_accounts()` populates from existing messages
  - Updates automatically when service selection changes
- **How To Button**: Scrollable quick-start guide (❓ How To)
  - Based on README content
  - Covers: Search, Browse, Export, Import, Supported Services
  - Directory structure, search types, privacy/security info
  - ESC key binding and Close button

### Version 0-4-2 (1114 lines) - Claude Support & Async Startup

#### Documentation & AI Guidance
- **Initial Request**: Generated comprehensive `.github/copilot-instructions.md` for AI agent development guidance
  - Documented core architecture (database layer, embedding engine, multi-service parser, Tkinter GUI)
  - Detailed data flow, JSON format detection patterns, and technical decisions
  - Included development workflows, common pitfalls, and integration points
  - ~150 lines covering project conventions and extension points

#### CSV Export Functionality
- **Export Feature**: Added dual CSV export system
  - All-services chronological export (sorted by timestamp)
  - Per-service individual exports (chatgpt, grok, claude, gemini, copilot)
  - Implemented cell content splitting for spreadsheet compatibility
  - Export menu with timestamped filenames: `chaits_all_YYYYMMDD_HHMMSS.csv`

#### Conversation Browser
- **Browse Interface**: Conversation list with multi-service filtering
  - Service checkboxes for all 5 services (All/None quick toggles)
  - Displays: Service, Account, Title, Message Count, Latest Timestamp
  - Sortable column headers (alphabetic for text, numeric for counts, date sorting)
  - Double-click to open full conversation view
  - Integrated "Find Related" and "Find Follow-ups" semantic search

#### UI/UX Improvements
- **Navigation & Controls**:
  - Red exit buttons on all dialogs for visibility
  - ESC key bindings on all popup windows for quick close
  - Focus management (`.focus_set()`) on all dialogs
  - Sortable treeview columns in main window and browser
  - "❓ How To" button with scrollable quick-start guide

#### Import Dialog Enhancement
- **Service/Account Selection**:
  - Replaced text prompts with dropdown/combobox interface
  - Service: Read-only dropdown with 5 supported services
  - Account: Editable combobox with autocomplete from database

#### Application Naming
- **Branding Evolution**: `chaitd` → `chait` → `chaits` (final)
  - Research showed "chait" had 7.6k GitHub results (mostly personal names)
  - Final rename to "chaits" for clarity and uniqueness
  - Updated across 4 files (28 string replacements)

#### Claude Integration
- **Data Format Support**: Fixed Claude conversation import
  - Root cause: Generic list parser catching Claude format prematurely
  - Solution: Moved Claude detection before generic list check in `parse_generic()`
  - Parser extracts from `chat_messages[]` arrays
  - **Result**: Successfully imported Claude conversations from test account

#### Startup Optimization
- **Async Loading**: Background thread for conversation indexing
  - GUI opens immediately instead of blocking during `auto_index()`
  - Status bar progression: "Starting up..." → "Indexing conversations..." → "Ready. All conversations indexed."
  - Thread-safe GUI updates using `app.after()` for status messages
  - Daemon thread ensures clean exit
  - **Impact**: Instant app responsiveness (no 10-15 second wait for embeddings model load)

#### Export Tool Enhancements
- **VS Code Copilot Exporter** (`export_vscode_copilot.py`):
  - Enhanced response parsing from `response.value[]` arrays
  - Improved handling of markdown/text content extraction
  - Fixed exit button positioning (small red button next to scan button)
  - Added ESC key binding for quick close
  - Output path management: `.aiccounts/accounts_copilot/{account}/exports/`

#### Technical Debt Resolved
- Fixed `MAX_CELL_CHARS` undefined error (missing newline in constant definition)
- Corrected Tkinter pack() ordering for proper button visibility
- Resolved focus management issues on popup windows
- Fixed status bar attribute error (created in `__init__` before thread access)
- Removed duplicate Claude parser (was appearing twice in `parse_generic()`)

#### Development Environment
- Python 3.x
- Dependencies: sqlite3, tkinter, numpy, sentence-transformers (all-MiniLM-L6-v2)
- Database: `db/chaits.sqlite`

---

## January 22, 2026 - VS Code Extension Integration

### Development Context
- **Chat Session**: "Configuring Copilot Chats for Time Tracking" (conversation_id: `<session_uuid>`)
- **Start Date**: Jan 22, 2026
- **User Request**: Enable system-wide tracking of per-message timestamps across all VS Code workspaces to facilitate accurate project timeline reconstruction
- **Solution**: Scaffold VS Code extension for system-wide per-message timestamp tracking

### Version 0-5-0 (1235 lines) - Extension Detection & Prompt System
- **Extension Detection Framework**: Auto-detect chaits-tracker extension installation
  - `is_extension_installed()`: Cross-platform detection (Windows/Linux/macOS)
  - Scans `~/.vscode/extensions/` for `chaits-tracker-*` directories
  - Checks global storage: `%APPDATA%/Code/User/globalStorage/chaits-tracker/` (Windows) or equivalent
  - Status tracking via `db/.extension_prompt_status` file
- **Prompt Management**: User-friendly extension installation flow
  - `get_prompt_status()` / `set_prompt_status()`: Persistent state management
  - Status values: "never", "dismissed", "installed"
  - Auto-check on startup (500ms delay after GUI loads)
  - "ignore always" option with "install" button if change-of-mind later
- **Requirements**: 
  - `export_vscode_copilot` must not rely on extension data to function
  - Extension setup facilitated from chaits first-run
  - User directives: GUI for beginners to set up initially alongside chaits
- **File Date**: Modified Jan 22, 2026

### chaits-tracker Extension (v0.1.0) - Initial Scaffold
- **Purpose**: Per-message timestamp tracking for Copilot chats across all workspaces
- **Problem Solved**: VS Code only stores session creation timestamps, not individual message times
  - Proper correlation of timeline crossovers can be frustrated by users needing to switch between chats intermittently during development
- **Core Features**:
  - Per-message timestamp capture for every user/assistant interaction
  - Cross-workspace unified timeline tracking
  - Cross-chat correlation within workspaces (agentic activity or topic switching)
  - Global storage syncs via Settings Sync to all machines
  - Privacy controls (optional timestamp-only mode without content)
- **Integration Features**:
  - Git commit timestamp correlation
  - File edit tracking and correlation
  - Workspace context preservation
- **Export Capabilities**:
  - Chaits-compatible JSON format
  - Auto-export (optional daily) to `.aiccounts` directory
  - Manual export with custom paths
  - Integration with `export_workspace_chats` tool (if extension present)
- **UI Components**:
  - Activity Bar view for timeline and settings
  - Status bar indicator showing active tracking
  - Timeline viewer for browsing recent interactions
  - User-friendly settings GUI panel
- **Installation Methods**:
  1. Auto-install via chaits main app (one-click, handles Node.js check)
  2. Manual build from source (`npm install`, `npm run compile`, `npm run package`)
- **Package Details**: TypeScript extension, requires VS Code 1.85.0+, Node.js 20.x
- **File Structure**:
  - `package.json`: Extension manifest (v0.1.0, 242 lines)
  - `src/`: TypeScript source files (extension.ts, exportManager.ts, settingsProvider.ts, timelineProvider.ts, timestampTracker.ts)
  - `media/`: Extension assets
  - `BUILD.md`, `INSTALL.md`, `QUICKSTART.md`: Documentation suite
  - `chaits-tracker-0.1.0.vsix`: Compiled extension package
- **Documentation Updates**:
  - Emoji cleanup: Removed unnecessary emoji from text/markdown docs (kept GUI labels)
  - `⏱️ tracked` → `time-tracked` for file-reader compatibility
  - Minimal Activity Bar icon approach
- **Created**: Jan 22, 2026 (all files in `chaits-tracker-extension/`)
- **Technical Issue**: IndentationError in chaits.0-5-0.py line 1430 (fixed same day)

---

## January 23, 2026 - Extension Installation Automation

### Development Context
- **Continuing Chat**: "Configuring Copilot Chats for Time Tracking" (same session from Jan 22)
- **User Requests**:
  - "will the tracker-extension be able to provide any [reliable] back-dated timestamps"
  - "can 'build' tracker-extension be done now, to have working code available for install popup"
  - "can include automation of build .vsix if not present, then continue with install it?"
  - "what if node.js/npm not installed"
- **Technical Issues Encountered**:
  - Build automation testing: renamed `node_modules/`, `out/`, `*.vsix` with `.old` suffix
  - TypeScript error TS6059: Files outside `rootDir` (resolved via tsconfig)
  - VS Code CLI install error: File not found (graceful fallback implemented)
  - Manual backup recovery: No backup before additions (used Ctrl+Z)

### Version 0-5-1 (1728 lines) - Auto-Build & Install Extension
- **Build Automation**: Integrated Node.js build system
  - `build_extension()`: Executes npm install → compile → package pipeline
  - Runs `npm install`, `npm run compile`, `vsce package` sequentially
  - Real-time output capture and display in dialog
  - Error handling with detailed diagnostics for TypeScript compilation issues
  - Handles missing dependencies (detects if renamed directories exist)
- **Installation Dialog**: Interactive extension setup UI
  - One-click installation workflow
  - Node.js detection with download prompt if missing (nodejs.org)
  - Live build progress display (scrollable text output)
  - VS Code CLI detection for `code --install-extension`
  - Status messages: "Building...", "Installing...", "Success!"
  - Option to dismiss or never show again
  - Red exit button + ESC key binding
  - Manual install instructions fallback if automation fails
- **Smart Prompting**: Conditional extension recommendation
  - `check_extension_prompt()`: Checks status on app startup
  - Only prompts if status is "never" (first run)
  - Updates status to "dismissed" or "installed" based on user choice
  - No repeated prompts after user decision
  - "ignore always" option persists across sessions
- **Extension Benefits Display**: Informational prompt explaining value
  - Enhanced timeline accuracy across workspace switches
  - Per-message timestamps (vs session-only timestamps)
  - Git commit correlation
  - Cross-chat tracking within workspaces for agentic workflows
  - Chaits-compatible export format
- **Technical Implementation**:
  - Subprocess execution with UTF-8 encoding
  - Output streaming to Text widget in real-time
  - Path validation for extension directory
  - VS Code CLI availability check (`code --version`)
  - Graceful fallback to manual instructions if CLI missing
  - tsconfig.json validation (exclude patterns for `.old` directories)
- **VSIX Packaging**:
  - System-independent package (safe for public repo)
  - Source code available in tracker-ext dir (not gitignored)
  - No privacy concerns in included files
  - Auto-build from source if .vsix not present
- **File Management**:
  - Version rollback: Current 0-5-0 saved as 0-5-1
  - No VSCode local history available (system restarted in interim)
  - Undo (Ctrl+Z) used to restore start-of-day state for 0-5-0
- **File Date**: Modified Jan 23, 2026
- **Line Count**: 1728 lines (+493 lines from v0-5-0)

### Documentation Updates
- **Extension Integration**: `chaits-ext.README.md` updated with installation methods
  - Documented auto-install via chaits (Option 1)
  - Manual build instructions (Option 2)
  - Node.js requirement clarifications with download links
- **Extension Welcome Text**: Updated to specify cross-chat correlation within workspaces
  - "Tracks all chats across every workspace, enabling accurate timeline reconstruction when you switch between projects"
  - Added context: "cross-chat time-correlation within workspaces too, for agentic activity or simply moving between chats for different topics"
- **README/Help**: Verified chaits.README.md and internal help text are current
- **Activity Focus**: Development concentrated on v0-5-1 (with v0-5-0 restored version maintained)

### Build Testing Process
1. Renamed build artifacts to test automation: `node_modules.old/`, `out.old/`, `*.vsix.old`
2. Encountered TypeScript TS6059 error (files outside rootDir)
3. Fixed tsconfig to exclude `.old` directories
4. Successfully built extension
5. VS Code CLI install failed (file not found error)
6. Implemented fallback to manual install instructions
7. Result: Working auto-build system with graceful degradation

### Development Timeline
- **v0-4-2** (Dec 27, 2025): Claude support, async startup, CSV exports (1114 lines)
- **v0-5-0** (Jan 22, 2026): Extension detection framework (1235 lines)
- **v0-5-1** (Jan 23, 2026): Auto-build and install extension (1728 lines)
- **Extension v0.1.0** (Jan 22, 2026): Initial chaits-tracker VS Code extension release

---

## Notes

This history file is sanitized for public distribution. For detailed development notes including specific system paths and account identifiers, see `chaits_hist/ai-hist_chaits.private.md` (not included in repository).
