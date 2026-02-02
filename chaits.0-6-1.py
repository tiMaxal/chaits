import sqlite3
import json
import csv
import hashlib
import threading
import time
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    SEMANTIC_AVAILABLE = True
except Exception:
    np = None
    SentenceTransformer = None
    SEMANTIC_AVAILABLE = False

# ===================== CONFIG =====================

APP_NAME = "chaits"
DB_PATH = Path("db/chaits.sqlite")

BASE_DIR = Path(".aiccounts")
SERVICE_DIRS = {
    "chatgpt": BASE_DIR / "accounts_chatgpt",
    "grok": BASE_DIR / "accounts_grok",
    "claude": BASE_DIR / "accounts_claude",
    "gemini": BASE_DIR / "accounts_gemini",
    "copilot": BASE_DIR / "accounts_copilot",
    "perplexity": BASE_DIR / "accounts_perplexity",
}

EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
SEMANTIC_LIMIT = 20
FOLLOWUP_SIMILARITY = 0.25
AUDIT_MODE = False  # Read-only mode
MAX_CELL_CHARS = 32000  # Excel/LibreOffice/OnlyOffice: 32767, Google Sheets: 50000 - using 32000 for compatibility

SEMANTIC_ENABLED = SEMANTIC_AVAILABLE

_model = None  # Lazy-loaded on first use

# Extension tracking
EXTENSION_CHECK_FILE = Path("db/.extension_prompt_status")

# ===================== EXTENSION DETECTION =====================

def is_extension_installed():
    """Check if chaits-tracker extension is installed in VS Code"""
    try:
        if os.name == 'nt':  # Windows
            global_storage = Path(os.environ.get('APPDATA', '')) / 'Code' / 'User' / 'globalStorage' / 'chaits-tracker'
            extensions_dir = Path(os.environ.get('USERPROFILE', '')) / '.vscode' / 'extensions'
        elif os.name == 'posix':
            if 'darwin' in os.sys.platform:  # Mac
                global_storage = Path.home() / 'Library' / 'Application Support' / 'Code' / 'User' / 'globalStorage' / 'chaits-tracker'
                extensions_dir = Path.home() / '.vscode' / 'extensions'
            else:  # Linux
                global_storage = Path.home() / '.config' / 'Code' / 'User' / 'globalStorage' / 'chaits-tracker'
                extensions_dir = Path.home() / '.vscode' / 'extensions'
        else:
            return False
        
        # Check if extension's global storage exists (it's active)
        if global_storage.exists():
            return True
        
        # Check if extension is installed (folder exists)
        if extensions_dir.exists():
            for ext_dir in extensions_dir.iterdir():
                if 'chaits-tracker' in ext_dir.name.lower():
                    return True
        
        return False
    except Exception:
        return False

def get_prompt_status():
    """Get the status of extension install prompt (never/later/ignored)"""
    if EXTENSION_CHECK_FILE.exists():
        try:
            status = EXTENSION_CHECK_FILE.read_text().strip()
            return status if status in ['ignored', 'later', 'installed'] else 'never'
        except:
            pass
    return 'never'

def set_prompt_status(status):
    """Save the prompt status"""
    try:
        EXTENSION_CHECK_FILE.parent.mkdir(exist_ok=True)
        EXTENSION_CHECK_FILE.write_text(status)
    except:
        pass

# ===================== EMBEDDINGS =====================

def get_model():
    """Lazy-load the sentence transformer model"""
    global _model
    if not SEMANTIC_AVAILABLE:
        raise RuntimeError("Semantic dependencies are not available")
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL_NAME)
    return _model

def embed_text(text: str) -> bytes:
    if not SEMANTIC_AVAILABLE:
        raise RuntimeError("Semantic dependencies are not available")
    vec = get_model().encode([text], normalize_embeddings=True)[0]
    return vec.astype(np.float32).tobytes()

def cosine_distance(a: bytes, b: bytes) -> float:
    if not SEMANTIC_AVAILABLE:
        return 1.0
    v1 = np.frombuffer(a, dtype=np.float32)
    v2 = np.frombuffer(b, dtype=np.float32)
    return 1.0 - float(np.dot(v1, v2))

# ===================== DATABASE =====================

def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.create_function("cosine_distance", 2, cosine_distance)
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY,
        service TEXT,
        account TEXT,
        conversation_id TEXT,
        conversation_title TEXT,
        timestamp_raw TEXT,
        timestamp_utc INTEGER,
        role TEXT,
        content TEXT,
        file_hash TEXT
    );

    CREATE UNIQUE INDEX IF NOT EXISTS uniq_msg
    ON messages(service, account, conversation_id, timestamp_utc, role, content);

    CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts
    USING fts5(content, content='messages', content_rowid='id');

    CREATE TABLE IF NOT EXISTS embeddings (
        message_id INTEGER PRIMARY KEY,
        embedding BLOB
    );

    CREATE TABLE IF NOT EXISTS conversation_tags (
        service TEXT,
        account TEXT,
        conversation_id TEXT,
        tag TEXT
    );

    CREATE TABLE IF NOT EXISTS pinned_conversations (
        service TEXT,
        account TEXT,
        conversation_id TEXT,
        pinned_at INTEGER
    );

    CREATE TRIGGER IF NOT EXISTS msg_ai AFTER INSERT ON messages BEGIN
        INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
    END;
    """)
    conn.commit()
    conn.close()

def semantic_ready() -> bool:
    return SEMANTIC_AVAILABLE and SEMANTIC_ENABLED

def try_install_semantic_deps() -> bool:
    """Attempt to install optional semantic dependencies via pip."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "sentence-transformers", "numpy"],
            capture_output=True,
            text=True,
            timeout=600
        )
        return result.returncode == 0
    except Exception:
        return False

def refresh_semantic_imports() -> bool:
    """Try to import semantic dependencies after installation."""
    global np, SentenceTransformer, SEMANTIC_AVAILABLE
    try:
        import numpy as _np
        from sentence_transformers import SentenceTransformer as _SentenceTransformer
        np = _np
        SentenceTransformer = _SentenceTransformer
        SEMANTIC_AVAILABLE = True
        return True
    except Exception:
        SEMANTIC_AVAILABLE = False
        return False

# ===================== IMPORT HELPERS =====================

def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(8192), b""):
            h.update(b)
    return h.hexdigest()

def normalize_timestamp(ts):
    if isinstance(ts, (int, float)):
        # Unix timestamp in seconds
        if ts > 1e12:  # Milliseconds
            return int(ts / 1000)
        return int(ts)
    if isinstance(ts, dict):
        # MongoDB extended JSON format: {"$date": {"$numberLong": "..."}}
        if "$date" in ts:
            date_val = ts["$date"]
            if isinstance(date_val, dict) and "$numberLong" in date_val:
                return int(date_val["$numberLong"]) // 1000
            elif isinstance(date_val, (int, float)):
                return int(date_val) // 1000
    try:
        return int(datetime.fromisoformat(ts).timestamp())
    except Exception:
        return None

def parse_copilot_csv(path: Path):
    """Parse Copilot desktop/web CSV export into conversation list."""
    convos = {}
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            required = {"Conversation", "Time", "Author", "Message"}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                return []
            for row in reader:
                title = (row.get("Conversation") or "Untitled").strip() or "Untitled"
                author = (row.get("Author") or "").strip().lower()
                role = "assistant" if author in ("ai", "assistant", "copilot", "bot") else "user"
                content = row.get("Message") or ""
                ts_raw = row.get("Time")
                convos.setdefault(title, {
                    "title": title,
                    "messages": []
                })
                convos[title]["messages"].append({
                    "role": role,
                    "content": content,
                    "create_time": ts_raw
                })
    except Exception:
        return []
    return list(convos.values())

def parse_generic(data):
    # ChatGPT format: root list with mapping field in each conversation
    if isinstance(data, list) and data and "mapping" in data[0]:
        return data  # Already in correct format, each item has title/mapping
    
    # Claude format: list of conversations with uuid, name, chat_messages[]
    # Must check BEFORE generic list format
    if isinstance(data, list) and data and "chat_messages" in data[0]:
        convos = []
        for conv in data:
            if not conv.get("chat_messages"):
                continue
            msgs = []
            for msg in conv["chat_messages"]:
                sender = msg.get("sender", "unknown")
                role = "user" if sender == "human" else "assistant"
                # Extract text from content array
                text = ""
                if isinstance(msg.get("content"), list):
                    for item in msg["content"]:
                        if item.get("type") == "text" and item.get("text"):
                            text += item["text"]
                msgs.append({
                    "role": role,
                    "content": text,
                    "create_time": msg.get("created_at")
                })
            if msgs:
                convos.append({
                    "id": conv.get("uuid"),
                    "title": conv.get("name", "Untitled"),
                    "messages": msgs
                })
        return convos

    # Perplexity-style: dict with messages[]
    if isinstance(data, dict) and isinstance(data.get("messages"), list):
        return [{
            "id": data.get("id"),
            "title": data.get("title", "Untitled"),
            "messages": data.get("messages", [])
        }]

    # Perplexity-style: dict with chat.messages[]
    if isinstance(data, dict) and isinstance(data.get("chat"), dict):
        chat = data.get("chat", {})
        if isinstance(chat.get("messages"), list):
            return [{
                "id": chat.get("id") or data.get("id"),
                "title": chat.get("title", data.get("title", "Untitled")),
                "messages": chat.get("messages", [])
            }]
    
    # Generic list format
    if isinstance(data, list):
        return [{"messages": data}]
    
    # Grok format: conversations[].{conversation, responses[]}
    if "conversations" in data and isinstance(data["conversations"], list):
        convos_list = data["conversations"]
        if convos_list and "conversation" in convos_list[0]:
            # Grok format detected
            result = []
            for item in convos_list:
                convo_meta = item.get("conversation", {})
                responses = item.get("responses", [])
                msgs = []
                for resp_wrapper in responses:
                    resp = resp_wrapper.get("response", {})
                    sender = resp.get("sender", "unknown")
                    role = "user" if sender == "human" else "assistant"
                    msgs.append({
                        "role": role,
                        "content": resp.get("message", ""),
                        "create_time": resp.get("create_time")
                    })
                if msgs:
                    result.append({
                        "id": convo_meta.get("id"),
                        "title": convo_meta.get("title", "Untitled"),
                        "messages": msgs
                    })
            return result
        else:
            # Standard conversations array (Copilot, etc)
            return data["conversations"]
    
    if "chats" in data:
        return data["chats"]
    if "conversation" in data:
        return [data]
    
    # Gemini/Google Takeout format with nested threads
    if "threads" in data:
        convos = []
        for thread in data["threads"]:
            msgs = []
            for turn in thread.get("turns", []):
                # Extract user messages
                if "userMessage" in turn:
                    msgs.append({
                        "role": "user",
                        "content": turn["userMessage"].get("text", ""),
                        "create_time": turn.get("timestamp")
                    })
                # Extract assistant messages
                if "assistantMessage" in turn:
                    msgs.append({
                        "role": "assistant",
                        "content": turn["assistantMessage"].get("text", ""),
                        "create_time": turn.get("timestamp")
                    })
            if msgs:
                convos.append({
                    "id": thread.get("id"),
                    "title": thread.get("title", "Untitled"),
                    "messages": msgs
                })
        return convos
    
    return []

# ===================== INDEXING =====================

def index_json(service, account, path):
    if AUDIT_MODE:
        return
    
    conn = None
    try:
        h = file_hash(path)
        conn = sqlite3.connect(DB_PATH)
        conn.create_function("cosine_distance", 2, cosine_distance)
        c = conn.cursor()

        if c.execute("SELECT 1 FROM messages WHERE file_hash=?", (h,)).fetchone():
            conn.close()
            return

        if path.suffix.lower() == ".csv":
            convos = parse_copilot_csv(path)
        else:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            convos = parse_generic(data)
        
        if not convos:
            print(f"Warning: No conversations found in {path}")
            conn.close()
            return

        for convo in convos:
            title = convo.get("title") or convo.get("conversation_title") or "Untitled"
            cid = convo.get("id") or convo.get("conversation_id") or hashlib.sha1((title + h).encode()).hexdigest()
            
            # Extract messages - handle both direct messages and mapping structure
            if "messages" in convo:
                msgs = convo["messages"]
            elif "mapping" in convo:
                # ChatGPT format: mapping has nodes, filter out None messages
                msgs = [node["message"] for node in convo["mapping"].values() 
                       if node.get("message") is not None]
            else:
                msgs = []

            for m in msgs:
                # Handle different message structures
                if "role" in m:
                    # Direct format (Copilot, Grok parsed)
                    role = m["role"]
                    content = m.get("content", "")
                elif "author" in m:
                    # ChatGPT format with author object
                    role = m.get("author", {}).get("role", "user")
                    content_obj = m.get("content", {})
                    if isinstance(content_obj, dict):
                        content = content_obj.get("parts", [""])[0] if content_obj.get("parts") else ""
                    else:
                        content = str(content_obj)
                else:
                    # Fallback
                    role = "user"
                    content = str(m.get("content", ""))
                
                if not content or not isinstance(content, str):
                    continue
                    
                ts_raw = m.get("create_time") or m.get("timestamp")
                ts_utc = normalize_timestamp(ts_raw)
                
                # Convert timestamp to string for storage (SQLite doesn't support dicts)
                if isinstance(ts_raw, dict):
                    ts_raw = json.dumps(ts_raw)
                
                try:
                    c.execute("""
                        INSERT INTO messages
                        (service, account, conversation_id, conversation_title,
                         timestamp_raw, timestamp_utc, role, content, file_hash)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (service, account, cid, title, ts_raw, ts_utc, role, content, h))
                    mid = c.lastrowid
                    if semantic_ready():
                        emb = embed_text(content)
                        c.execute("INSERT INTO embeddings VALUES (?,?)", (mid, emb))
                except sqlite3.IntegrityError:
                    pass
        conn.commit()
        conn.close()
        
    except json.JSONDecodeError as e:
        print(f"JSON parse error in {path}: {e}")
        if conn:
            conn.close()
    except Exception as e:
        print(f"Failed to index {path}: {e}")
        if conn:
            conn.close()

def auto_index():
    for service, base in SERVICE_DIRS.items():
        base.mkdir(exist_ok=True)
        for acc in base.iterdir():
            if not acc.is_dir():
                continue
            
            # Index JSON/CSV files in account root directory
            for j in acc.glob("*.json"):
                index_json(service, acc.name, j)
            for j in acc.glob("*.csv"):
                index_json(service, acc.name, j)
            
            # Also index files in exports/ subdirectory
            exp = acc / "exports"
            if exp.exists():
                for j in exp.glob("*.json"):
                    index_json(service, acc.name, j)
                for j in exp.glob("*.csv"):
                    index_json(service, acc.name, j)

# ===================== SEARCH =====================

def fts_search(query):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    rows = c.execute("""
        SELECT m.id, m.service, m.account, m.conversation_title,
               m.timestamp_raw, m.role, m.content
        FROM messages_fts f
        JOIN messages m ON f.rowid=m.id
        WHERE f.content MATCH ?
        ORDER BY m.timestamp_utc DESC
        LIMIT 500
    """, (query,)).fetchall()
    conn.close()
    return rows

def semantic_search(text):
    if not semantic_ready():
        raise RuntimeError("Semantic search is disabled or unavailable")
    qemb = embed_text(text)
    conn = sqlite3.connect(DB_PATH)
    conn.create_function("cosine_distance", 2, cosine_distance)
    c = conn.cursor()
    rows = c.execute("""
        SELECT m.id, m.service, m.account, m.conversation_title,
               m.timestamp_raw, m.role, m.content,
               cosine_distance(e.embedding, ?) AS score
        FROM embeddings e
        JOIN messages m ON m.id=e.message_id
        ORDER BY score ASC
        LIMIT ?
    """, (qemb, SEMANTIC_LIMIT)).fetchall()
    conn.close()
    return rows

def hybrid_search(query, limit=200):
    if not semantic_ready():
        raise RuntimeError("Hybrid search is disabled or unavailable")
    qemb = embed_text(query)
    conn = sqlite3.connect(DB_PATH)
    conn.create_function("cosine_distance", 2, cosine_distance)
    c = conn.cursor()
    rows = c.execute("""
        SELECT m.id, m.service, m.account, m.conversation_title,
               m.timestamp_raw, m.role, m.content,
               bm25(messages_fts) AS fts_rank,
               cosine_distance(e.embedding, ?) AS sem_score
        FROM messages_fts f
        JOIN messages m ON f.rowid=m.id
        JOIN embeddings e ON e.message_id=m.id
        WHERE f.content MATCH ?
        LIMIT ?
    """, (qemb, query, limit)).fetchall()
    conn.close()
    ranked = sorted(rows, key=lambda r: 0.6*r[7]+0.4*r[8])
    return ranked

def similar_other_accounts(mid, account):
    if not semantic_ready():
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.create_function("cosine_distance", 2, cosine_distance)
    c = conn.cursor()
    emb = c.execute("SELECT embedding FROM embeddings WHERE message_id=?", (mid,)).fetchone()
    if not emb:
        return []
    rows = c.execute("""
        SELECT m.id, m.service, m.account, m.conversation_title,
               m.timestamp_raw, m.role, m.content,
               cosine_distance(e.embedding, ?) AS score
        FROM embeddings e
        JOIN messages m ON m.id=e.message_id
        WHERE m.account != ?
        ORDER BY score ASC
        LIMIT ?
    """, (emb[0], account, SEMANTIC_LIMIT)).fetchall()
    conn.close()
    return rows

def followups(mid):
    if not semantic_ready():
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.create_function("cosine_distance", 2, cosine_distance)
    c = conn.cursor()
    emb, ts = c.execute("""
        SELECT e.embedding, m.timestamp_utc
        FROM embeddings e JOIN messages m ON m.id=e.message_id
        WHERE m.id=?
    """, (mid,)).fetchone()
    rows = c.execute("""
        SELECT m.id, m.service, m.account, m.conversation_title,
               m.timestamp_raw, m.role, m.content,
               cosine_distance(e.embedding, ?) AS score
        FROM embeddings e
        JOIN messages m ON m.id=e.message_id
        WHERE m.timestamp_utc > ?
          AND cosine_distance(e.embedding, ?) < ?
        ORDER BY m.timestamp_utc ASC
        LIMIT ?
    """, (emb, ts, emb, FOLLOWUP_SIMILARITY, SEMANTIC_LIMIT)).fetchall()
    conn.close()
    return rows

# ===================== EXPORT =====================

def split_content_to_rows(row_data, content_index=7):
    """
    Split a row if content exceeds MAX_CELL_CHARS.
    Returns list of rows with duplicated metadata and suffixed roles.
    
    Args:
        row_data: tuple of row values
        content_index: index of content field (default 7)
    """
    content = row_data[content_index]
    if len(content) <= MAX_CELL_CHARS:
        return [row_data]
    
    # Split content into chunks
    chunks = []
    for i in range(0, len(content), MAX_CELL_CHARS):
        chunks.append(content[i:i+MAX_CELL_CHARS])
    
    # Create rows with suffixed roles
    result_rows = []
    role_index = 6  # Role is at index 6
    for idx, chunk in enumerate(chunks, 1):
        new_row = list(row_data)
        new_row[content_index] = chunk
        new_row[role_index] = f"{row_data[role_index]}_{idx}"
        result_rows.append(tuple(new_row))
    
    return result_rows

def add_conversation_sequence_numbers(rows):
    """
    Add sequential suffixes to conversation titles to preserve order.
    Format: ' _01', ' _02', ' _03' etc (with space before underscore)
    """
    # Group by conversation_id (index 2)
    from collections import defaultdict
    convo_sequences = defaultdict(int)
    
    result_rows = []
    for row in rows:
        row_list = list(row)
        convo_id = row[2]
        convo_sequences[convo_id] += 1
        seq_num = convo_sequences[convo_id]
        
        # Add sequence suffix to conversation title (index 3)
        original_title = row[3]
        row_list[3] = f"{original_title} _{seq_num:02d}"
        
        result_rows.append(tuple(row_list))
    
    return result_rows

def export_service_csv(service, output_path):
    """Export all messages for a specific service to CSV with content splitting"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    rows = c.execute("""
        SELECT service, account, conversation_id, conversation_title,
               timestamp_utc, timestamp_raw, role, content
        FROM messages
        WHERE service = ?
        ORDER BY timestamp_utc ASC
    """, (service,)).fetchall()
    conn.close()
    
    # Add sequence numbers to conversation titles
    rows = add_conversation_sequence_numbers(rows)
    
    # Split content that exceeds cell limit
    final_rows = []
    for row in rows:
        final_rows.extend(split_content_to_rows(row))
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Service', 'Account', 'Conversation_ID', 'Conversation_Title',
                        'Timestamp_UTC', 'Timestamp_Raw', 'Role', 'Content'])
        writer.writerows(final_rows)
    return len(final_rows)

def export_all_csv(output_path):
    """Export all messages from all services, chronologically sorted with content splitting"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    rows = c.execute("""
        SELECT service, account, conversation_id, conversation_title,
               timestamp_utc, timestamp_raw, role, content
        FROM messages
        ORDER BY timestamp_utc ASC
    """).fetchall()
    conn.close()
    
    # Add sequence numbers to conversation titles
    rows = add_conversation_sequence_numbers(rows)
    
    # Split content that exceeds cell limit
    final_rows = []
    for row in rows:
        final_rows.extend(split_content_to_rows(row))
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Service', 'Account', 'Conversation_ID', 'Conversation_Title',
                        'Timestamp_UTC', 'Timestamp_Raw', 'Role', 'Content'])
        writer.writerows(final_rows)
    return len(final_rows)

def export_search_results_csv(output_path, tree_items):
    """Export currently displayed search results to CSV"""
    if not tree_items:
        return 0
    
    # Add sequence numbers and split content
    final_rows = []
    for item in tree_items:
        # tree_items format: (Service, Account, Conversation, Time, Role, Snippet)
        # Convert to full row format
        row = (item[0], item[1], item[2], item[2], None, item[3], item[4], item[5])
        final_rows.extend(split_content_to_rows(row))
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Service', 'Account', 'Conversation_ID', 'Conversation_Title',
                        'Timestamp_UTC', 'Timestamp_Raw', 'Role', 'Content'])
        writer.writerows(final_rows)
    return len(final_rows)

def get_conversations(services=None):
    """
    Get list of conversations, optionally filtered by service(s).
    Returns: [(service, account, conversation_id, conversation_title, msg_count, latest_timestamp)]
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if services:
        placeholders = ','.join('?' * len(services))
        query = f"""
            SELECT service, account, conversation_id, conversation_title,
                   COUNT(*) as msg_count, MAX(timestamp_utc) as latest
            FROM messages
            WHERE service IN ({placeholders})
            GROUP BY service, account, conversation_id
            ORDER BY latest DESC
        """
        rows = c.execute(query, services).fetchall()
    else:
        rows = c.execute("""
            SELECT service, account, conversation_id, conversation_title,
                   COUNT(*) as msg_count, MAX(timestamp_utc) as latest
            FROM messages
            GROUP BY service, account, conversation_id
            ORDER BY latest DESC
        """).fetchall()
    
    conn.close()
    return rows

# ===================== GUI =====================

class Chaits(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("chaits — Cross-AI Chat Index & Discovery Tool")
        self.geometry("1200x800")

        top = tk.Frame(self)
        top.pack(fill="x")
        self.q = tk.Entry(top, font=("Arial", 14))
        self.q.pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(top, text="Keyword", command=self.keyword).pack(side="left")
        self.btn_semantic = tk.Button(top, text="Semantic", command=self.semantic)
        self.btn_semantic.pack(side="left")
        self.btn_hybrid = tk.Button(top, text="Hybrid", command=self.hybrid)
        self.btn_hybrid.pack(side="left")
        tk.Button(top, text="🔄 Refresh", command=self.manual_refresh).pack(side="left")
        tk.Button(top, text="📁 Import", command=self.import_file).pack(side="left")
        tk.Button(top, text="📊 Export", command=self.export_menu).pack(side="left")
        tk.Button(top, text="💬 Conversations", command=self.browse_conversations).pack(side="left")
        tk.Button(top, text="❓ How To", command=self.show_howto).pack(side="left")
        tk.Button(top, text="Exit", command=self.quit, bg="red", fg="white").pack(side="right", padx=5)
        tk.Button(top, text="❤️", command=self.show_donation, fg="#e74c3c", font=("Arial", 10)).pack(side="right", padx=2)

        cols = ("Service","Account","Conversation","Time","Role","Snippet")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        
        # Configure columns with stretch enabled for proper resizing
        for c in cols:
            self.tree.column(c, stretch=True)
        
        # Set up sortable headers
        for c in cols:
            self.tree.heading(c, text=c,
                            command=lambda col=c: self.sort_results(col, False))
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.open_convo)
        
        # Status bar at bottom
        self.status_bar = tk.Label(self, text="Ready", relief="sunken", anchor="w")
        self.status_bar.pack(side="bottom", fill="x")
        
        # Check for extension after UI is ready
        self.after(500, self.check_extension_prompt)

    def fill(self, rows):
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            snip = r[6][:200]
            self.tree.insert("", "end", iid=r[0], values=(r[1],r[2],r[3],r[4],r[5],snip))
    
    def sort_results(self, col, reverse):
        """Sort main window results by column"""
        # Get all items
        items = [(self.tree.set(item, col), item) for item in self.tree.get_children('')]
        
        # Alphabetic sort (all columns are text in main view)
        items.sort(key=lambda x: x[0].lower(), reverse=reverse)
        
        # Rearrange items in sorted order
        for index, (val, item) in enumerate(items):
            self.tree.move(item, '', index)
        
        # Update heading to reverse sort next time
        self.tree.heading(col, command=lambda: self.sort_results(col, not reverse))

    def keyword(self):
        self.fill(fts_search(self.q.get()))

    def semantic(self):
        if not semantic_ready():
            messagebox.showwarning(
                "Semantic Search Disabled",
                "Semantic search is unavailable because optional dependencies are not installed."
            )
            return
        self.fill(semantic_search(self.q.get()))

    def hybrid(self):
        if not semantic_ready():
            messagebox.showwarning(
                "Hybrid Search Disabled",
                "Hybrid search is unavailable because optional dependencies are not installed."
            )
            return
        self.fill(hybrid_search(self.q.get()))

    def open_convo(self, _):
        mid = int(self.tree.focus())
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        svc, acc, cid = c.execute("""
            SELECT service, account, conversation_id FROM messages WHERE id=?
        """, (mid,)).fetchone()
        msgs = c.execute("""
            SELECT id, timestamp_raw, role, content
            FROM messages
            WHERE service=? AND account=? AND conversation_id=?
            ORDER BY timestamp_utc
        """, (svc,acc,cid)).fetchall()
        conn.close()

        self.show_conversation_window(svc, acc, cid, msgs, focus_mid=mid)

    def show_conversation_window(self, service, account, conversation_id, msgs, focus_mid=None):
        """Render a conversation window from a list of messages."""
        w = tk.Toplevel(self)
        w.title(f"{service}/{account}")
        w.geometry("800x600")
        w.bind("<Escape>", lambda e: w.destroy())
        
        # Frame for text with scrollbar
        text_frame = tk.Frame(w)
        text_frame.pack(fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
        
        t = tk.Text(text_frame, wrap="word", yscrollcommand=scrollbar.set)
        t.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=t.yview)

        for mid2, ts, r, ctext in msgs:
            t.insert("end", f"[{ts}] {r.upper()}:\n{ctext}\n\n")

        btn_frame = tk.Frame(w)
        btn_frame.pack(fill="x", pady=5)
        if focus_mid is not None:
            if semantic_ready():
                tk.Button(btn_frame, text="Similar (other accounts)",
                          command=lambda: self.show(similar_other_accounts(focus_mid, account))).pack(side="left", padx=5)
                tk.Button(btn_frame, text="Find follow-ups",
                          command=lambda: self.show(followups(focus_mid))).pack(side="left", padx=5)
            else:
                tk.Button(btn_frame, text="Similar (other accounts)", state="disabled").pack(side="left", padx=5)
                tk.Button(btn_frame, text="Find follow-ups", state="disabled").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Exit", command=w.destroy, bg="red", fg="white").pack(side="right", padx=5)
        
        w.focus_set()

    def show(self, rows):
        w = tk.Toplevel(self)
        t = ttk.Treeview(w, columns=("S","A","C","T","R","Score"), show="headings")
        for c in t["columns"]:
            t.heading(c, text=c)
        t.pack(fill="both", expand=True)
        for r in rows:
            t.insert("", "end", values=(r[1],r[2],r[3],r[4],r[5],f"{r[7]:.2f}"))

    def manual_refresh(self):
        """Trigger indexing on demand"""
        self.config(cursor="wait")
        self.update()
        try:
            auto_index()
            messagebox.showinfo("Refresh", "Index updated successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Indexing failed: {e}")
        finally:
            self.config(cursor="")

    def import_file(self):
        """Import specific JSON file"""
        path = filedialog.askopenfilename(
            title="Select Export File",
            filetypes=[("JSON or CSV files", "*.json;*.csv"), ("JSON files", "*.json"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not path:
            return
        
        # Create dialog for service and account selection
        dialog = tk.Toplevel(self)
        dialog.title("Import File")
        dialog.geometry("400x200")
        dialog.bind("<Escape>", lambda e: dialog.destroy())
        dialog.focus_set()
        
        result = {}
        
        # Service dropdown
        tk.Label(dialog, text="Select Service:", font=("Arial", 10, "bold")).pack(pady=(10, 5))
        service_var = tk.StringVar()
        service_combo = ttk.Combobox(dialog, textvariable=service_var, state="readonly", width=30)
        service_combo['values'] = list(SERVICE_DIRS.keys())
        service_combo.pack(pady=5)
        service_combo.current(0)
        
        # Account combobox with autocomplete
        tk.Label(dialog, text="Account Name:", font=("Arial", 10, "bold")).pack(pady=(10, 5))
        account_var = tk.StringVar()
        account_combo = ttk.Combobox(dialog, textvariable=account_var, width=30)
        account_combo.pack(pady=5)
        
        def update_account_list(event=None):
            """Update account dropdown based on selected service"""
            service = service_var.get()
            if service:
                accounts = self.get_existing_accounts(service)
                account_combo['values'] = accounts
        
        service_combo.bind("<<ComboboxSelected>>", update_account_list)
        update_account_list()  # Initial population
        
        def on_ok():
            service = service_var.get()
            account = account_var.get().strip()
            if not service or not account:
                messagebox.showwarning("Missing Info", "Please select service and enter account name")
                return
            result['service'] = service
            result['account'] = account
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        # Buttons
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=15)
        tk.Button(btn_frame, text="OK", command=on_ok, bg="lightgreen", width=10).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", command=on_cancel, bg="red", fg="white", width=10).pack(side="left", padx=5)
        
        dialog.wait_window()
        
        if not result:
            return
        
        try:
            index_json(result['service'], result['account'], Path(path))
            messagebox.showinfo("Success", f"Imported {Path(path).name}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def get_existing_accounts(self, service):
        """Get list of existing accounts for a service"""
        try:
            conn = get_db()
            rows = conn.execute(
                "SELECT DISTINCT account FROM messages WHERE service = ? ORDER BY account",
                (service,)
            ).fetchall()
            return [row[0] for row in rows]
        except Exception:
            return []
    
    def export_menu(self):
        """Show export options dialog"""
        dialog = tk.Toplevel(self)
        dialog.title("Export Chat Data")
        dialog.geometry("400x320")
        dialog.bind("<Escape>", lambda e: dialog.destroy())
        
        tk.Label(dialog, text="Export Options", font=("Arial", 14, "bold")).pack(pady=10)
        
        tk.Button(dialog, text="Export Search Results (Current View)",
                 command=lambda: self.do_export_search_results(dialog)).pack(pady=5, padx=20, fill="x")
        
        tk.Button(dialog, text="Export All Services (Chronological)",
                 command=lambda: self.do_export_all(dialog)).pack(pady=5, padx=20, fill="x")
        
        tk.Label(dialog, text="Export by Service:", font=("Arial", 10)).pack(pady=10)
        
        for service in SERVICE_DIRS.keys():
            tk.Button(dialog, text=f"Export {service.title()}",
                     command=lambda s=service: self.do_export_service(s, dialog)).pack(pady=2, padx=20, fill="x")
        
        tk.Button(dialog, text="Exit", command=dialog.destroy, bg="red", fg="white").pack(pady=10, padx=20, fill="x")
        
        dialog.focus_set()
    
    def do_export_search_results(self, dialog):
        """Export currently displayed search results"""
        # Get all items from tree
        tree_items = []
        for item in self.tree.get_children():
            tree_items.append(self.tree.item(item)['values'])
        
        if not tree_items:
            messagebox.showwarning("No Results", "No search results to export. Please run a search first.")
            return
        
        path = filedialog.asksaveasfilename(
            title="Export Search Results",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"chaits_search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        if not path:
            return
        
        try:
            count = export_search_results_csv(path, tree_items)
            messagebox.showinfo("Export Complete", f"Exported {count} messages to:\n{path}")
            dialog.destroy()
        except Exception as e:
            messagebox.showerror("Export Error", str(e))
    
    def do_export_all(self, dialog):
        """Export all services chronologically"""
        path = filedialog.asksaveasfilename(
            title="Export All Services",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"chaits_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        if not path:
            return
        
        try:
            count = export_all_csv(path)
            messagebox.showinfo("Export Complete", f"Exported {count} messages to:\n{path}")
            dialog.destroy()
        except Exception as e:
            messagebox.showerror("Export Error", str(e))
    
    def do_export_service(self, service, dialog):
        """Export specific service data"""
        path = filedialog.asksaveasfilename(
            title=f"Export {service.title()} Data",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"chaits_{service}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        if not path:
            return
        
        try:
            count = export_service_csv(service, path)
            if count == 0:
                messagebox.showwarning("No Data", f"No messages found for {service}")
            else:
                messagebox.showinfo("Export Complete", f"Exported {count} messages to:\n{path}")
            dialog.destroy()
        except Exception as e:
            messagebox.showerror("Export Error", str(e))
    
    def show_donation(self):
        """Show donation information and open donation page"""
        # Placeholder URL - to be updated when timax.al donation page is ready
        donation_url = "https://timax.al/HTML/donate"
        
        message = (
            "Support chaits Development\n\n"
            "If you find chaits useful, consider supporting its development!\n\n"
            "Your contribution helps maintain and improve this tool.\n\n"
            "Donation options: Fiat and/or Crypto\n\n"
            "Click OK to open the donation page in your browser."
        )
        
        if messagebox.askyesno("Support chaits", message, icon="info"):
            try:
                import webbrowser
                webbrowser.open(donation_url)
            except Exception as e:
                messagebox.showerror("Error", f"Could not open browser: {e}\n\nPlease visit: {donation_url}")
    
    def show_howto(self):
        """Display quick guide based on README"""
        w = tk.Toplevel(self)
        w.title("How To Use chaits")
        w.geometry("700x650")
        w.focus_set()
        w.bind("<Escape>", lambda e: w.destroy())
        
        # Main frame with scrollbar
        frame = tk.Frame(w)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")
        
        text = tk.Text(frame, wrap="word", yscrollcommand=scrollbar.set, font=("Segoe UI", 10))
        text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=text.yview)
        
        howto_text = """chaits - Cross-AI Chat Index & Discovery Tool

AI-voding [vibe-coding] in VS-Code with Copilot by tiMaxal.
 .. this is directed AI code creation, not written by a competent coder; all care possible has been taken, but no responsibility accepted for use by others!

QUICK START:

1. SEARCH
   • Enter query in search box
   • Click Keyword/Semantic/Hybrid search
   • Hybrid combines both (60% keyword + 40% semantic)
   • Click column headers to sort results

2. BROWSE CONVERSATIONS
   • Click 💬 Conversations button
   • Filter by service (check/uncheck boxes)
   • Click column headers to sort
   • Double-click to view full conversation

3. VIEW CONVERSATION
   • Double-click any result to see full history
   • Use "🔍 Find Related" to discover similar chats
   • Navigate between messages

4. EXPORT DATA
   • Click 📊 Export button
   • Export Search Results: Save current search view as CSV
   • Export All: Chronological CSV of all services
   • Export by Service: Individual service CSVs
   • Compatible with LibreOffice/Excel/OnlyOffice

5. IMPORT CONVERSATIONS
   • Export from AI services:
     - ChatGPT: Settings → Export data
     - Grok: Browser dev tools (API responses)
     - Claude/Gemini: Export from web interface
    • For VS Code Copilot: Run export_vscode_copilot.py
    • For Copilot desktop/web: CSV export is supported
   • Place JSON in .aiccounts/accounts_{service}/{account}/exports/
   • Click 🔄 Refresh or 📁 Import

ENHANCED TIMELINE TRACKING:
   • Install chaits-tracker VS Code extension for per-message timestamps
   • Enables accurate timeline reconstruction across workspace switches
   • Settings → check for "Install Extension" prompt

SUPPORTED SERVICES:
    • ChatGPT  • Claude  • Gemini  • Grok  • GitHub Copilot  • Perplexity

DIRECTORY STRUCTURE:
   .aiccounts/accounts_{service}/{account}/exports/*.json
   Example: .aiccounts/accounts_chatgpt/myaccount/exports/conversations.json

SEARCH TYPES:
   • Keyword: Fast text matching (SQLite FTS5)
   • Semantic: AI-powered similarity (embeddings)
   • Hybrid: Best of both worlds

PRIVACY & SECURITY:
   [+] Fully offline - no network calls
   [+] All data stored locally
   [+] No credentials stored
   [+] Read-only audit mode available

KEYBOARD SHORTCUTS:
   • ESC: Close dialogs
   • Double-click: View conversation details

For more details, see chaits.README.md"""
        
        text.insert("1.0", howto_text)
        text.config(state="disabled")
        
        tk.Button(w, text="Close", command=w.destroy, bg="lightblue").pack(pady=5)
    
    def browse_conversations(self):
        """Browse and select conversations by service"""
        browser = tk.Toplevel(self)
        browser.title("Conversation Browser")
        browser.geometry("900x600")
        browser.bind("<Escape>", lambda e: browser.destroy())
        
        # Service filter frame
        filter_frame = tk.Frame(browser)
        filter_frame.pack(fill="x", pady=5)
        
        tk.Label(filter_frame, text="Filter by Service:").pack(side="left", padx=5)
        
        # Service checkboxes
        service_vars = {}
        for service in SERVICE_DIRS.keys():
            var = tk.BooleanVar(value=True)
            service_vars[service] = var
            tk.Checkbutton(filter_frame, text=service.title(), variable=var,
                          command=lambda: self.update_conversation_list(browser, service_vars, tree)).pack(side="left")
        
        tk.Button(filter_frame, text="All",
                 command=lambda: self.set_all_services(service_vars, True, browser, tree)).pack(side="left", padx=5)
        tk.Button(filter_frame, text="None",
                 command=lambda: self.set_all_services(service_vars, False, browser, tree)).pack(side="left")
        
        # Conversation list
        cols = ("Service", "Account", "Title", "Messages", "Latest")
        tree = ttk.Treeview(browser, columns=cols, show="headings")
        
        # Configure columns with stretch enabled and initial widths
        tree.column("Service", width=80, stretch=True)
        tree.column("Account", width=100, stretch=True)
        tree.column("Title", width=400, stretch=True)
        tree.column("Messages", width=80, stretch=True)
        tree.column("Latest", width=150, stretch=True)
        
        # Set up sortable headers
        for col in cols:
            tree.heading(col, text=col, 
                        command=lambda c=col: self.sort_conversations(tree, c, False))
        
        scrollbar = ttk.Scrollbar(browser, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True, pady=(0, 5))
        
        tree.bind("<Double-1>", lambda e: self.open_conversation_from_browser(tree, e))
        
        # Exit button
        tk.Button(browser, text="Exit", command=browser.destroy, bg="red", fg="white").pack(pady=5, padx=20, fill="x")
        
        # Initial load
        self.update_conversation_list(browser, service_vars, tree)
        browser.focus_set()
    
    def set_all_services(self, service_vars, value, browser, tree):
        """Set all service checkboxes to value"""
        for var in service_vars.values():
            var.set(value)
        self.update_conversation_list(browser, service_vars, tree)
    
    def sort_conversations(self, tree, col, reverse):
        """Sort conversation tree by column"""
        # Get all items
        items = [(tree.set(item, col), item) for item in tree.get_children('')]
        
        # Sort items - handle numeric columns specially
        if col == "Messages":
            items.sort(key=lambda x: int(x[0]), reverse=reverse)
        elif col == "Latest":
            # Sort by date string (YYYY-MM-DD HH:MM format sorts correctly)
            items.sort(key=lambda x: x[0], reverse=reverse)
        else:
            # Alphabetic sort
            items.sort(key=lambda x: x[0].lower(), reverse=reverse)
        
        # Rearrange items in sorted order
        for index, (val, item) in enumerate(items):
            tree.move(item, '', index)
        
        # Update heading to reverse sort next time
        tree.heading(col, command=lambda: self.sort_conversations(tree, col, not reverse))
    
    def update_conversation_list(self, browser, service_vars, tree):
        """Update conversation list based on selected services"""
        selected_services = [s for s, var in service_vars.items() if var.get()]
        
        tree.delete(*tree.get_children())
        
        if not selected_services:
            return
        
        convos = get_conversations(selected_services)
        
        for convo in convos:
            service, account, cid, title, msg_count, latest_ts = convo
            # Format timestamp
            if latest_ts:
                latest_str = datetime.fromtimestamp(latest_ts).strftime('%Y-%m-%d %H:%M')
            else:
                latest_str = "Unknown"
            
            tree.insert("", "end", values=(service, account, title, msg_count, latest_str),
                       tags=(service, account, cid))
    
    def open_conversation_from_browser(self, tree, event=None):
        """Open selected conversation from browser"""
        item_id = None
        if event is not None:
            item_id = tree.identify_row(event.y)
        if not item_id:
            selection = tree.selection()
            if selection:
                item_id = selection[0]
        if not item_id:
            return
        
        tags = tree.item(item_id, "tags")
        if len(tags) < 3:
            return
        
        service, account, cid = tags[0], tags[1], tags[2]
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        msgs = c.execute("""
            SELECT id, timestamp_raw, role, content
            FROM messages
            WHERE service=? AND account=? AND conversation_id=?
            ORDER BY timestamp_utc
        """, (service, account, cid)).fetchall()
        conn.close()
        
        if not msgs:
            messagebox.showinfo("No Messages", "This conversation has no messages.")
            return
        
        self.show_conversation_window(service, account, cid, msgs)
    
    def check_extension_prompt(self):
        """Check if user should be prompted about chaits-tracker extension"""
        # Don't prompt if already installed
        if is_extension_installed():
            return
        
        status = get_prompt_status()
        
        # Don't prompt if user chose "Never"
        if status == 'ignored':
            return
        
        # Prompt user
        self.show_extension_install_dialog()

    def set_semantic_ui_state(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.btn_semantic.config(state=state)
        self.btn_hybrid.config(state=state)
        if enabled:
            self.status_bar.config(text="Ready. Semantic search enabled.")
        else:
            self.status_bar.config(text="Ready. Semantic search disabled (optional deps missing).")

    def check_semantic_prompt(self):
        """Prompt to install semantic dependencies or disable semantic features."""
        global SEMANTIC_ENABLED
        if SEMANTIC_AVAILABLE:
            self.set_semantic_ui_state(True)
            return

        choice = messagebox.askyesnocancel(
            "Optional Features",
            "Semantic search requires optional dependencies (sentence-transformers, numpy).\n\n"
            "Yes: Install now (uses disk space)\n"
            "No: Continue without semantic features\n"
            "Cancel: Exit"
        )

        if choice is None:
            self.quit()
            return

        if choice:
            self.status_bar.config(text="Installing semantic dependencies...")
            self.update()
            if try_install_semantic_deps() and refresh_semantic_imports():
                SEMANTIC_ENABLED = True
                self.set_semantic_ui_state(True)
                messagebox.showinfo(
                    "Install Complete",
                    "Dependencies installed. You may need to restart the app if semantic search doesn't work immediately."
                )
            else:
                SEMANTIC_ENABLED = False
                self.set_semantic_ui_state(False)
                messagebox.showwarning(
                    "Install Failed",
                    "Could not install dependencies. Semantic features will be disabled."
                )
        else:
            SEMANTIC_ENABLED = False
            self.set_semantic_ui_state(False)
    
    def build_extension(self, ext_dir):
        """Build the VS Code extension package. Returns True on success."""
        try:
            print("\n++ Building chaits-tracker extension...")
            
            # Check for required tools
            npm_cmd = self.find_npm_command()
            if not npm_cmd:
                print("[-] npm not found - Node.js required")
                messagebox.showerror("Build Error", "npm not found - Node.js required")
                return False
            
            # Step 1: npm install
            print("  + Running npm install...")
            result = subprocess.run([npm_cmd, 'install'],
                                  cwd=str(ext_dir),
                                  capture_output=True,
                                  text=True,
                                  timeout=120)
            if result.returncode != 0:
                error_msg = f"npm install failed:\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
                print(f"[-] {error_msg}")
                messagebox.showerror("Build Error", error_msg[:500])  # Truncate for dialog
                return False
            
            # Step 2: npm run compile
            print("  + Compiling TypeScript...")
            result = subprocess.run([npm_cmd, 'run', 'compile'],
                                  cwd=str(ext_dir),
                                  capture_output=True,
                                  text=True,
                                  timeout=60)
            if result.returncode != 0:
                error_msg = f"Compile failed:\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
                print(f"[-] {error_msg}")
                messagebox.showerror("Build Error", error_msg[:500])  # Truncate for dialog
                return False
            
            # Step 3: Check for vsce, install if needed
            vsce_cmd = self.find_vsce_command()
            if not vsce_cmd:
                print("  + Installing vsce...")
                result = subprocess.run([npm_cmd, 'install', '-g', '@vscode/vsce'],
                                      capture_output=True,
                                      text=True,
                                      timeout=60)
                if result.returncode != 0:
                    error_msg = f"Failed to install vsce:\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
                    print(f"[-] {error_msg}")
                    messagebox.showerror("Build Error", error_msg[:500])
                    return False
                vsce_cmd = self.find_vsce_command()
                if not vsce_cmd:
                    print("[-] vsce still not found after installation")
                    messagebox.showerror("Build Error", "vsce still not found after installation")
                    return False
            
            # Step 4: Package extension
            print("  + Packaging extension...")
            result = subprocess.run([vsce_cmd, 'package', '--allow-missing-repository'],
                                  cwd=str(ext_dir),
                                  capture_output=True,
                                  text=True,
                                  timeout=60)
            if result.returncode != 0:
                error_msg = f"Packaging failed:\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
                print(f"[-] {error_msg}")
                messagebox.showerror("Build Error", error_msg[:500])
                return False
            
            print("[+] Extension built successfully!")
            return True
            
        except subprocess.TimeoutExpired:
            print("[-] Build timed out")
            messagebox.showerror("Build Error", "Build timed out")
            return False
        except Exception as e:
            error_msg = f"Build error: {e}"
            print(f"[-] {error_msg}")
            messagebox.showerror("Build Error", error_msg)
            return False
    
    def find_npm_command(self):
        """Find npm command (npm.cmd on Windows)"""
        if os.name == 'nt':
            # Windows - try npm.cmd
            npm_paths = [
                'npm.cmd',
                r'C:\Program Files\nodejs\npm.cmd',
                Path(os.environ.get('APPDATA', '')) / 'npm' / 'npm.cmd'
            ]
            for npm in npm_paths:
                try:
                    subprocess.run([str(npm), '--version'], capture_output=True, timeout=5)
                    return str(npm)
                except:
                    pass
        else:
            # Unix-like
            try:
                subprocess.run(['npm', '--version'], capture_output=True, timeout=5)
                return 'npm'
            except:
                pass
        return None
    
    def find_vsce_command(self):
        """Find vsce command (vsce.cmd on Windows)"""
        if os.name == 'nt':
            # Windows - try vsce.cmd
            vsce_paths = [
                'vsce.cmd',
                Path(os.environ.get('APPDATA', '')) / 'npm' / 'vsce.cmd'
            ]
            for vsce in vsce_paths:
                try:
                    subprocess.run([str(vsce), '--version'], capture_output=True, timeout=5)
                    return str(vsce)
                except:
                    pass
        else:
            # Unix-like
            try:
                subprocess.run(['vsce', '--version'], capture_output=True, timeout=5)
                return 'vsce'
            except:
                pass
        return None
    
    def find_vscode_command(self):
        """Find VS Code CLI command"""
        if os.name == 'nt':
            # Windows - try multiple locations
            code_paths = [
                'code.cmd',
                'code',
                Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'Microsoft VS Code' / 'bin' / 'code.cmd',
                Path(os.environ.get('PROGRAMFILES', 'C:\\Program Files')) / 'Microsoft VS Code' / 'bin' / 'code.cmd',
                Path(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)')) / 'Microsoft VS Code' / 'bin' / 'code.cmd',
            ]
            for code_cmd in code_paths:
                try:
                    result = subprocess.run([str(code_cmd), '--version'], 
                                          capture_output=True, timeout=5)
                    if result.returncode == 0:
                        return str(code_cmd)
                except:
                    pass
        else:
            # Unix-like
            try:
                result = subprocess.run(['code', '--version'], capture_output=True, timeout=5)
                if result.returncode == 0:
                    return 'code'
            except:
                pass
        return None
    
    def show_extension_install_dialog(self):
        """Show dialog to install chaits-tracker extension"""
        dialog = tk.Toplevel(self)
        dialog.title("Enhanced Timeline Tracking")
        dialog.geometry("600x400")
        dialog.transient(self)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (dialog.winfo_screenheight() // 2) - (400 // 2)
        dialog.geometry(f"600x400+{x}+{y}")
        
        # Content frame
        content = tk.Frame(dialog, padx=20, pady=20)
        content.pack(fill="both", expand=True)
        
        # Title
        title = tk.Label(content, text="Accurate Timeline Tracking Available",
                        font=("Arial", 14, "bold"))
        title.pack(pady=(0, 10))
        
        # Description
        desc = tk.Text(content, wrap="word", height=10, font=("Arial", 10))
        desc.pack(fill="both", expand=True, pady=10)
        
        desc.insert("1.0", """VS Code currently only stores when Copilot conversations start, not when individual messages were sent.

The chaits-tracker extension solves this by recording exact timestamps for every interaction. This enables:

[+] Accurate reconstruction of development timelines
[+] Tracking work across multiple projects
[+] Understanding when you actually did what
[+] Correlation with Git commits and file edits

Installation is one-click and syncs to all your machines via Settings Sync.

Would you like to install the extension now?
""")
        desc.config(state="disabled")
        
        # Button frame
        button_frame = tk.Frame(content)
        button_frame.pack(pady=10)
        
        def install_extension():
            set_prompt_status('installed')
            dialog.destroy()
            
            ext_dir = Path(__file__).parent / "chaits-tracker-extension"
            vsix_file = ext_dir / "chaits-tracker-0.1.0.vsix"
            
            # Auto-build if .vsix doesn't exist
            if not vsix_file.exists() and ext_dir.exists():
                # Check for Node.js/npm first
                npm_cmd = self.find_npm_command()
                if not npm_cmd:
                    response = messagebox.askyesno(
                        "Node.js Required",
                        "Extension needs to be built, but Node.js/npm is not installed.\n\n"
                        "Options:\n"
                        "1. Install Node.js from https://nodejs.org/ then try again\n"
                        "2. Ask someone to build it for you (creates .vsix file)\n"
                        "3. Use chaits without the extension (session-level timestamps only)\n\n"
                        "Would you like to open the Node.js download page?")
                    if response:
                        import webbrowser
                        webbrowser.open('https://nodejs.org/')
                    return
                
                build_result = self.build_extension(ext_dir)
                if not build_result:
                    messagebox.showerror("Build Failed", 
                                       "Could not build extension automatically.\n\n"
                                       "See chaits-tracker-extension/BUILD.md for manual instructions.")
                    return
            
            # Install the .vsix
            if vsix_file.exists():
                # Find VS Code CLI
                code_cmd = self.find_vscode_command()
                if not code_cmd:
                    messagebox.showwarning("Manual Installation Required",
                                         f"VS Code 'code' command not found in PATH.\n\n"
                                         f"To install manually:\n\n"
                                         f"1. Open VS Code\n"
                                         f"2. Press Ctrl+Shift+P\n"
                                         f"3. Type: Extensions: Install from VSIX\n"
                                         f"4. Select: {vsix_file.absolute()}\n\n"
                                         f"Alternative: Add VS Code to PATH\n"
                                         f"(VS Code → Ctrl+Shift+P → 'Shell Command: Install code command in PATH')")
                    return
                
                try:
                    print(f"++ Installing extension using: {code_cmd}")
                    result = subprocess.run([code_cmd, '--install-extension', str(vsix_file.absolute())],
                                          capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        messagebox.showinfo("Success", 
                                          "Extension installed successfully!\n\n"
                                          "Please restart VS Code to activate tracking.\n\n"
                                          "The extension will automatically record timestamps "
                                          "for all future Copilot chats.")
                    else:
                        messagebox.showerror("Error", 
                                           f"Installation failed:\n{result.stderr}\n\n"
                                           "You can install manually: See chaits-tracker-extension/INSTALL.md")
                except Exception as e:
                    messagebox.showerror("Error", 
                                       f"Could not install extension:\n{e}\n\n"
                                       "You can install manually: See chaits-tracker-extension/INSTALL.md")
            else:
                messagebox.showerror("Extension Not Found",
                                   "Extension source code not found.\n\n"
                                   "Please ensure chaits-tracker-extension/ directory exists.")
        
        def remind_later():
            set_prompt_status('later')
            dialog.destroy()
        
        def never_show():
            set_prompt_status('ignored')
            dialog.destroy()
        
        tk.Button(button_frame, text="✅ Install Extension", command=install_extension,
                 bg="#4CAF50", fg="white", font=("Arial", 10, "bold"),
                 padx=15, pady=5).pack(side="left", padx=5)
        
        tk.Button(button_frame, text="⏰ Remind Me Later", command=remind_later,
                 font=("Arial", 10), padx=15, pady=5).pack(side="left", padx=5)
        
        tk.Button(button_frame, text="🚫 Don't Ask Again", command=never_show,
                 font=("Arial", 10), padx=15, pady=5).pack(side="left", padx=5)
    
    def install_extension_dialog(self):
        """Show instructions for installing the extension"""
        dialog = tk.Toplevel(self)
        dialog.title("Install chaits-tracker Extension")
        dialog.geometry("700x500")
        dialog.transient(self)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (700 // 2)
        y = (dialog.winfo_screenheight() // 2) - (500 // 2)
        dialog.geometry(f"700x500+{x}+{y}")
        
        content = tk.Frame(dialog, padx=20, pady=20)
        content.pack(fill="both", expand=True)
        
        title = tk.Label(content, text="Installing chaits-tracker Extension",
                        font=("Arial", 14, "bold"))
        title.pack(pady=(0, 10))
        
        instructions = tk.Text(content, wrap="word", font=("Arial", 10))
        instructions.pack(fill="both", expand=True, pady=10)
        
        ext_dir = Path("chaits-tracker-extension")
        vsix_file = ext_dir / "chaits-tracker-0.1.0.vsix"
        
        if vsix_file.exists():
            # Extension package exists - show install command
            instructions.insert("1.0", f"""[+] Extension package found!

OPTION 1: Install via Command Line
----------------------------------
1. Open a terminal/command prompt
2. Run this command:

   code --install-extension "{vsix_file.absolute()}"

3. Restart VS Code when prompted


OPTION 2: Install via VS Code
------------------------------
1. Open VS Code
2. Press Ctrl+Shift+X (Extensions view)
3. Click the ⋯ menu (three dots at top)
4. Select "Install from VSIX..."
5. Navigate to: {vsix_file.absolute()}
6. Click Install
7. Restart VS Code when prompted


After Installation:
-------------------
• You'll see a welcome screen explaining the features
• Status bar will show: [Chaits]
• Tracking starts automatically
• Data syncs via VS Code Settings Sync

Click "Open Folder" below to open the extension directory.
""")
            
            button_frame = tk.Frame(content)
            button_frame.pack(pady=10)
            
            def open_folder():
                if os.name == 'nt':
                    os.startfile(ext_dir.absolute())
                elif os.name == 'posix':
                    subprocess.run(['open' if 'darwin' in os.sys.platform else 'xdg-open', 
                                  str(ext_dir.absolute())])
            
            def install_now():
                try:
                    result = subprocess.run(['code', '--install-extension', str(vsix_file.absolute())],
                                          capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        messagebox.showinfo("Success", 
                                          "Extension installed! Please restart VS Code to activate it.")
                        dialog.destroy()
                    else:
                        messagebox.showerror("Error", 
                                           f"Installation failed:\n{result.stderr}")
                except Exception as e:
                    messagebox.showerror("Error", f"Could not install extension:\n{e}")
            
            tk.Button(button_frame, text="🚀 Install Now", command=install_now,
                     bg="#4CAF50", fg="white", font=("Arial", 10, "bold"),
                     padx=15, pady=5).pack(side="left", padx=5)
            
            tk.Button(button_frame, text="📁 Open Folder", command=open_folder,
                     font=("Arial", 10), padx=15, pady=5).pack(side="left", padx=5)
            
        else:
            # Extension needs to be built
            instructions.insert("1.0", f"""[!] Extension needs to be built first

The extension source code is in: {ext_dir.absolute()}

To build and install:
---------------------
1. Open a terminal in the extension directory:
   cd "{ext_dir.absolute()}"

2. Install dependencies:
   npm install

3. Build the extension:
   npm run compile
   npm run package

4. Install the generated .vsix file:
   code --install-extension chaits-tracker-0.1.0.vsix

5. Restart VS Code


Need Help?
----------
See BUILD.md in the extension directory for detailed instructions.
See INSTALL.md for a beginner-friendly guide.
""")
            
            button_frame = tk.Frame(content)
            button_frame.pack(pady=10)
            
            def open_folder():
                if os.name == 'nt':
                    os.startfile(ext_dir.absolute())
                elif os.name == 'posix':
                    subprocess.run(['open' if 'darwin' in os.sys.platform else 'xdg-open',
                                  str(ext_dir.absolute())])
            
            tk.Button(button_frame, text="📁 Open Extension Folder", command=open_folder,
                     font=("Arial", 10, "bold"), padx=15, pady=5).pack(side="left", padx=5)
        
        instructions.config(state="disabled")
        
        tk.Button(content, text="Close", command=dialog.destroy,
                 padx=20, pady=5).pack(pady=10)
    
    def show_conversation(self, service, account, conv_id):
        """Show full conversation content"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""SELECT message_id, create_time, role, content 
                      FROM messages 
                      WHERE service=? AND account=? AND conversation_id=?
                      ORDER BY create_time""", (service, account, conv_id))
        msgs = cur.fetchall()
        conn.close()
        
        w = tk.Toplevel(self)
        w.title(f"{service}/{account}")
        w.geometry("800x600")
        w.bind("<Escape>", lambda e: w.destroy())
        
        t = tk.Text(w, wrap="word")
        t.pack(fill="both", expand=True)
        
        for mid, ts, r, ctext in msgs:
            t.insert("end", f"[{ts}] {r.upper()}:\n{ctext}\n\n")
        
        btn_frame = tk.Frame(w)
        btn_frame.pack(fill="x", pady=5)
        tk.Button(btn_frame, text="Similar (other accounts)",
                 command=lambda: self.show(similar_other_accounts(msgs[0][0], account))).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Find follow-ups",
                 command=lambda: self.show(followups(msgs[0][0]))).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Exit", command=w.destroy, bg="red", fg="white").pack(side="right", padx=5)
        
        w.focus_set()

# ===================== MAIN =====================

def background_index(app):
    """Run auto_index in background thread"""
    try:
        app.after(0, lambda: app.status_bar.config(text="Indexing conversations..."))
        auto_index()
        app.after(0, lambda: app.status_bar.config(text="Ready. All conversations indexed."))
    except Exception as e:
        app.after(0, lambda: app.status_bar.config(text=f"Indexing error: {e}"))

if __name__ == "__main__":
    init_db()
    app = Chaits()
    app.status_bar.config(text="Starting up...")
    # Ensure semantic feature choice is applied before indexing
    app.check_semantic_prompt()
    # Start indexing in background after UI is ready
    threading.Thread(target=background_index, args=(app,), daemon=True).start()
    app.mainloop()
