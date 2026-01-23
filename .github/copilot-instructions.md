# chaits Development Guide

**Cross-AI Chat Index & Discovery Tool** — Local, offline desktop app for indexing, searching, and semantically correlating conversations across AI services.

## Development History & Context

### Timeline
- **Dec 20, 2025**: Initial development (Session: `75e4e758-b03e-4c4e-b356-4ca855cc6cbc`)
  - Core concept: GUI app to search across multiple AI account histories
  - Manual JSON export workflow established
  - VS Code workspace storage discovery for Copilot chats
  - Original name: "chaitd"
- **Dec 21-27, 2025**: Feature development across multiple sessions
  - CSV export system, conversation browser, import dialog
  - Claude integration, async startup optimization
  - Application renamed: chaitd → chait → **chaits** (final)
  - Directory rename documented in `chaits_hist/ai-hist_chaits.md`
- **Current Status**: All development chats from Dec 20-27 extracted and available in `.aiccounts/accounts_copilot/timax/exports/vscode_copilot_dev_timeline_20251220-27.json`

### Key Context for Continuation
When working on this project, you're continuing development that began Dec 20. The original development chat is Session `75e4e758-b03e-4c4e-b356-4ca855cc6cbc` from workspace hash `970aad19...` (pre-rename). Current development should build on established patterns and decisions from that timeline. See `chaits_hist/ai-hist_chaits.md` for detailed version history.

## Project Architecture

### Core Components
- **Database Layer** (`chaits.py` lines 50-105): SQLite with FTS5 for keyword search, custom embeddings table for semantic search
- **Embedding Engine** (`chait.py` lines 32-48): Uses SentenceTransformer `all-MiniLM-L6-v2` with lazy loading, stores as float32 bytes
- **Multi-Service Parser** (`chait.py` lines 135-210): Handles ChatGPT, Grok, Claude, Gemini, Copilot JSON export formats
- **Tkinter GUI** (`chait.py` lines 420-537): Keyword/semantic/hybrid search, conversation drill-down, cross-account linking
- **Export Tool** (`export_vscode_copilot.py`): Extracts Copilot chat history from VS Code's workspace storage

### Data Flow
```
Manual JSON exports → Account directories → auto_index() → 
parse_generic() detects format → SQLite + embeddings → 
GUI search (FTS5/semantic/hybrid) → conversation view → followup analysis
```

## Multi-Service Data Structure

### Directory Layout
```
.aiccounts/accounts_{service}/{account}/exports/*.json
├─ .aiccounts/accounts_chatgpt/553rdd4-chatgpt/conversations.json
├─ .aiccounts/accounts_grok/553rdd4-grok/prod-grok-backend.json
├─ .aiccounts/accounts_copilot/timax/exports/vscode_copilot_*.json
└─ .aiccounts/accounts_gemini/, accounts_claude/
```

### JSON Format Detection (`parse_generic`)
- **ChatGPT**: Root list with `mapping` field containing node structure
- **Grok**: `conversations[].{conversation, responses[]}` with `sender: "human"`
- **Copilot**: Standard `conversations[]` array with `messages[]`
- **Gemini**: `threads[].turns[]` with `userMessage`/`assistantMessage`
- **Generic**: Falls back to `messages` or `chats` arrays

### Message Normalization
```python
# Extracted structure regardless of source:
{
    "role": "user" | "assistant",
    "content": str,
    "create_time": int (Unix timestamp) | dict (MongoDB format)
}
```

## Key Technical Decisions

### Embedding Strategy
- **Lazy loading**: Model loads on first `embed_text()` call to avoid startup delay
- **Normalization**: All embeddings L2-normalized before storage for cosine similarity
- **Storage**: Binary blob format (float32) for efficient SQLite storage
- **Dimension**: 384 (fixed by all-MiniLM-L6-v2)

### Hybrid Search Ranking
```python
# chait.py line 372
ranked = sorted(rows, key=lambda r: 0.6*r[7]+0.4*r[8])
# 60% FTS5 BM25, 40% semantic cosine distance
```

### Timestamp Handling (`normalize_timestamp`)
Converts multiple formats to Unix seconds:
- Raw Unix timestamps (seconds or milliseconds)
- MongoDB extended JSON: `{"$date": {"$numberLong": "..."}}`
- ISO 8601 strings
- Stores raw format as JSON string, normalized as integer

### Security Model
- **`AUDIT_MODE = False`**: When True, disables all DB writes (read-only correlation)
- **No network calls**: All processing is local
- **No credential storage**: Relies on manual JSON exports
- **Hash-based deduplication**: `file_hash()` prevents re-indexing

## Development Workflows

### Running the App
```bash
python chaits.py  # Initializes DB, indexes all accounts, launches GUI
```

### Extracting Copilot History
```bash
python export_vscode_copilot.py                    # GUI mode
python export_vscode_copilot.py --cli              # CLI mode
python export_vscode_copilot.py --output file.json # Custom output
```
Scans `%APPDATA%\Code\User\workspaceStorage\*/chatSessions/*.json` for session files.

### Adding New Export Sources
1. Place JSON in `{service}_accounts/{account}/exports/`
2. Click "🔄 Refresh" or use "📁 Import" to specify service/account manually
3. `auto_index()` recursively scans `*.json` in account root and `exports/` subdirectory

### Testing Parser Extensions
Extend `parse_generic()` (lines 135-210) to detect new JSON schemas:
```python
# Example pattern:
if "new_field" in data:
    return [{"messages": transform(data["new_field"])}]
```

## Project Conventions

### Versioning Pattern
Files like `chaitd.0-1-0.py`, `chaitd.0-1-1.py` are iteration snapshots. Working version is always `chaits.py`.

### Configuration Constants
```python
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"  # SentenceTransformer model
SEMANTIC_LIMIT = 20                     # Max results for semantic search
FOLLOWUP_SIMILARITY = 0.25              # Cosine distance threshold
AUDIT_MODE = False                      # Set True for read-only mode
```

### Database Schema
- **messages**: Core table with service/account/conversation/role/content
- **messages_fts**: FTS5 virtual table for keyword search
- **embeddings**: Binary embeddings indexed by message_id
- **conversation_tags**, **pinned_conversations**: Future feature tables (unused)

## Integration Points

### VS Code Copilot Storage
Path: `%APPDATA%\Code\User\workspaceStorage\<hash>\chatSessions\*.json`
Format: `{sessionId, customTitle, creationDate, requests[{message, response}]}`

### External Dependencies
```
sentence-transformers  # Embedding model
numpy                  # Vector operations
```
No API keys required — fully offline.

## Common Pitfalls

1. **Empty JSON exports**: Some services export metadata-only files. Check `parse_generic()` returns non-empty list.
2. **Timestamp formats**: New services may use unsupported formats. Extend `normalize_timestamp()` (lines 117-133).
3. **Model download**: First run downloads `all-MiniLM-L6-v2` (~80MB) from HuggingFace.
4. **SQLite locking**: GUI runs on main thread. Long indexing blocks UI — consider threading for large imports.
5. **Copilot fragmentation**: VS Code stores chats per workspace. Export tool must scan all workspace directories.

## Future Extension Points

- **API Integration**: Replace manual exports with service APIs (noted in `ai-hist_chaits.md`)
- **Database Encryption**: SQLite encryption for sensitive aggregated data
- **Polling Logic**: Currently manual refresh only (removed auto-poll to reduce resource usage)
- **Conversation Clustering**: Mentioned in README but not yet implemented
