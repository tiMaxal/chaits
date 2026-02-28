"""
Export VS Code Copilot chats for a specific workspace to Markdown files.

Saves chats chronologically as markdown files in the workspace's .vscode/copilot_history/
directory to preserve them when workspace directories are renamed.

Usage:
    python export_workspace_chats.py                # GUI mode - pick workspace
    python export_workspace_chats.py --list         # List all workspaces
    python export_workspace_chats.py --workspace "path/to/workspace"  # Export specific workspace
    python export_workspace_chats.py --current      # Export for current workspace (auto-detect)
"""

import json
import os
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from datetime import datetime
import argparse
import threading
from urllib.parse import unquote, urlparse

def load_extension_timestamps():
    """
    Load per-message timestamps from chaits-tracker extension if available.
    Returns dict mapping sessionId -> list of timestamps.
    Gracefully returns empty dict if extension not installed.
    """
    def candidate_global_storage_dirs():
        candidates = []

        if os.name == 'nt':  # Windows
            appdata = Path(os.environ.get('APPDATA', ''))
            products = [
                'Code', 'Code - Insiders', 'VSCodium', 'Code - OSS',
                'Cursor', 'Cursor - Insiders'
            ]
            for product in products:
                candidates.append(appdata / product / 'User' / 'globalStorage')
        elif os.name == 'posix':
            if 'darwin' in os.sys.platform:  # Mac
                base = Path.home() / 'Library' / 'Application Support'
                products = ['Code', 'Code - Insiders', 'VSCodium', 'Code - OSS', 'Cursor']
                for product in products:
                    candidates.append(base / product / 'User' / 'globalStorage')
            else:  # Linux
                base = Path.home() / '.config'
                products = ['Code', 'Code - Insiders', 'VSCodium', 'Code - OSS', 'Cursor']
                for product in products:
                    candidates.append(base / product / 'User' / 'globalStorage')

        # Filter to existing
        return [c for c in candidates if c.exists()]

    try:
        global_storage_dirs = candidate_global_storage_dirs()
        if not global_storage_dirs:
            return {}

        print("  ++ Loading chaits-tracker extension data...")
        session_timestamps = {}

        for base_dir in global_storage_dirs:
            global_storage = base_dir / 'chaits-tracker' / 'interaction-logs'
            if not global_storage.exists():
                continue

            for session_file in global_storage.glob('session-*.jsonl'):
                session_id = session_file.stem.replace('session-', '')
                timestamps = []

                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                interaction = json.loads(line)
                                timestamps.append({
                                    'timestamp': interaction['timestamp'],
                                    'role': interaction['role']
                                })

                    if timestamps:
                        if session_id not in session_timestamps or len(timestamps) > len(session_timestamps[session_id]):
                            session_timestamps[session_id] = timestamps
                except Exception:
                    pass

        if session_timestamps:
            print(f"  + Enhanced timestamps available for {len(session_timestamps)} sessions")

        return session_timestamps
    except Exception:
        return {}

def get_workspace_storage_dir():
    """Get VS Code workspace storage directory"""
    if os.name == 'nt':  # Windows
        return Path(os.environ['APPDATA']) / 'Code' / 'User' / 'workspaceStorage'
    elif os.name == 'posix':
        if 'darwin' in os.sys.platform:  # Mac
            return Path.home() / 'Library' / 'Application Support' / 'Code' / 'User' / 'workspaceStorage'
        else:  # Linux
            return Path.home() / '.config' / 'Code' / 'User' / 'workspaceStorage'
    else:
        raise OSError("Unsupported OS")

def find_workspaces_with_chats():
    """
    Find all workspaces that have chat history.
    Returns list of dicts with workspace info.
    """
    workspace_storage = get_workspace_storage_dir()
    if not workspace_storage.exists():
        return []
    
    workspaces = []
    
    for workspace_dir in workspace_storage.iterdir():
        if not workspace_dir.is_dir():
            continue
        
        chat_sessions_dir = workspace_dir / 'chatSessions'
        if not chat_sessions_dir.exists():
            continue
        
        # Count chat sessions with actual content
        session_files = list(chat_sessions_dir.glob('*.json'))
        if not session_files:
            continue
        
        # Count only non-empty sessions
        valid_session_count = 0
        for session_file in session_files:
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    session = json.load(f)
                    requests = session.get('requests', [])
                    # Only count sessions with actual requests
                    if requests:
                        valid_session_count += 1
            except:
                pass
        
        # Skip workspaces with no valid sessions
        if valid_session_count == 0:
            continue
        
        # Try to get workspace name from workspace.json
        workspace_json = workspace_dir / 'workspace.json'
        workspace_name = None
        workspace_path = None
        
        if workspace_json.exists():
            try:
                with open(workspace_json, 'r', encoding='utf-8') as f:
                    ws_data = json.load(f)
                    # Extract folder path if available
                    if 'folder' in ws_data:
                        folder_uri = ws_data['folder']
                        # Parse file:/// URI properly
                        if folder_uri.startswith('file://'):
                            # Use urlparse and unquote for proper URI handling
                            parsed = urlparse(folder_uri)
                            workspace_path = unquote(parsed.path)
                            # On Windows, remove leading slash from /C:/path
                            if os.name == 'nt' and len(workspace_path) > 2 and workspace_path[0] == '/' and workspace_path[2] == ':':
                                workspace_path = workspace_path[1:]
                            workspace_name = Path(workspace_path).name
            except:
                pass
        
        workspaces.append({
            'hash': workspace_dir.name,
            'name': workspace_name or f"Workspace {workspace_dir.name[:8]}",
            'path': workspace_path,
            'storage_dir': workspace_dir,
            'chat_count': valid_session_count
        })
    
    return workspaces

def generate_title_precis(messages, max_length=50):
    """Generate a concise title from the first user message"""
    if not messages:
        return "empty_chat"
    
    # Find first user message
    first_user = next((m for m in messages if m.get('role') == 'user'), None)
    if not first_user:
        return "untitled_chat"
    
    content = first_user.get('content', '').strip()
    if not content:
        return "untitled_chat"
    
    # Take first line or sentence
    first_line = content.split('\n')[0]
    if len(first_line) > max_length:
        first_line = first_line[:max_length] + "..."
    
    # Clean for filename
    clean = re.sub(r'[^\w\s-]', '', first_line)
    clean = re.sub(r'[\s_]+', '_', clean)
    clean = clean.strip('_').lower()
    
    return clean or "untitled_chat"

def export_chat_to_markdown(conversation, output_path):
    """Export a single conversation to markdown format"""
    messages = conversation.get('messages', [])
    title = conversation.get('conversation_title', 'Untitled Chat')
    create_time = conversation.get('create_time', 0)

    def format_msg_timestamp(ts_value):
        if not ts_value:
            return "Unknown time"
        try:
            # Extension timestamps are stored in ms
            if isinstance(ts_value, (int, float)) and ts_value > 1e12:
                return datetime.fromtimestamp(ts_value / 1000).strftime('%Y-%m-%d %H:%M:%S')
            if isinstance(ts_value, (int, float)):
                return datetime.fromtimestamp(ts_value).strftime('%Y-%m-%d %H:%M:%S')
            return str(ts_value)
        except Exception:
            return "Unknown time"
    
    # Format creation date
    if create_time:
        date_str = datetime.fromtimestamp(create_time).strftime('%Y-%m-%d %H:%M:%S')
    else:
        date_str = 'Unknown'
    
    # Build markdown content
    md_lines = [
        f"# {title}",
        "",
        f"**Created:** {date_str}  ",
        f"**Messages:** {len(messages)}  ",
        "",
        "---",
        ""
    ]
    
    for i, msg in enumerate(messages, 1):
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')
        msg_ts = format_msg_timestamp(msg.get('timestamp'))
        heading_prefix = f"[{i:03d}] {msg_ts} — "
        
        if role == 'user':
            md_lines.append(f"## {heading_prefix}👤 User")
        elif role == 'assistant':
            md_lines.append(f"## {heading_prefix}🤖 Assistant")
        else:
            md_lines.append(f"## {heading_prefix}{role.title()}")
        
        md_lines.append("")
        md_lines.append(content)
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))

def extract_text_recursive(obj, max_depth=5, current_depth=0):
    """Recursively extract text content from nested structures"""
    if current_depth > max_depth:
        return []
    
    texts = []
    
    if isinstance(obj, str):
        if obj.strip():
            texts.append(obj)
    elif isinstance(obj, dict):
        # Common text fields to check
        for key in ['value', 'text', 'content', 'message', 'data', 'markdown']:
            if key in obj:
                texts.extend(extract_text_recursive(obj[key], max_depth, current_depth + 1))
        # If nothing found, search all values
        if not texts:
            for value in obj.values():
                texts.extend(extract_text_recursive(value, max_depth, current_depth + 1))
    elif isinstance(obj, list):
        for item in obj:
            texts.extend(extract_text_recursive(item, max_depth, current_depth + 1))
    
    return texts

def export_workspace_chats_to_md(workspace_info, output_dir=None, debug=False, conflict_mode='suffix', use_subdirs=True):
    """
    Export all chats for a specific workspace as numbered markdown files.
    
    Args:
        workspace_info: Dict with workspace metadata
        output_dir: Custom output directory (defaults to workspace/.vscode/copilot_history)
        debug: If True, save unparseable responses to debug file
        conflict_mode: How to handle existing files - 'overwrite' or 'suffix'
        use_subdirs: If True and output_dir is set, create workspace subdirectories
    
    Returns:
        Number of chats exported, output path
    """
    storage_dir = workspace_info['storage_dir']
    chat_sessions_dir = storage_dir / 'chatSessions'
    
    # Determine output directory
    if output_dir:
        if use_subdirs:
            # Create subdirectory for this workspace in custom output directory
            # Use workspace name if available, otherwise use hash
            if workspace_info['name'] and workspace_info['name'] != f"Workspace {workspace_info['hash'][:8]}":
                # Clean workspace name for directory use
                clean_name = re.sub(r'[<>:"/\\|?*]', '_', workspace_info['name'])
                subdir_name = clean_name
            else:
                subdir_name = workspace_info['hash'][:16]  # Use first 16 chars of hash
            
            output_path = Path(output_dir) / subdir_name
        else:
            # Use custom directory directly without subdirectories
            output_path = Path(output_dir)
    elif workspace_info['path']:
        # Save in workspace's .vscode/copilot_history
        output_path = Path(workspace_info['path']) / '.vscode' / 'copilot_history'
    else:
        # Fallback to current directory
        output_path = Path.cwd() / 'copilot_exports' / workspace_info['hash']
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load extension timestamps if available
    extension_timestamps = load_extension_timestamps()
    
    # Load and sort all conversations by creation date
    conversations = []
    
    for session_file in chat_sessions_dir.glob('*.json'):
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session = json.load(f)
            
            # Extract session metadata
            session_id = session.get('sessionId', session_file.stem)
            title = session.get('customTitle', 'Untitled Chat')
            creation_date = session.get('creationDate', 0)
            requests = session.get('requests', [])
            
            if not requests:
                continue
            
            # Check if we have extension timestamps for this session
            has_extension_data = session_id in extension_timestamps
            timestamp_index = 0
            
            # Convert to messages
            messages = []
            unparseable_responses = []
            
            for req_idx, req in enumerate(requests):
                # Extract user message
                if 'message' in req and req['message']:
                    user_text = req['message'].get('text', '')
                    if user_text:
                        msg = {"role": "user", "content": user_text}
                        # Add per-message timestamp if available
                        if has_extension_data and timestamp_index < len(extension_timestamps[session_id]):
                            ts_data = extension_timestamps[session_id][timestamp_index]
                            if ts_data['role'] == 'user':
                                msg["timestamp"] = ts_data['timestamp']
                                timestamp_index += 1
                        messages.append(msg)
                
                # Extract assistant response
                if 'response' in req and req['response']:
                    response_content = []
                    response_obj = req['response']
                    
                    # Method 1: Extract from value array if present
                    if 'value' in response_obj and isinstance(response_obj['value'], list):
                        for item in response_obj['value']:
                            if isinstance(item, dict):
                                # Text content
                                if 'value' in item and isinstance(item['value'], str):
                                    response_content.append(item['value'])
                                # Markdown content
                                elif 'value' in item and isinstance(item['value'], dict):
                                    if 'value' in item['value']:
                                        response_content.append(str(item['value']['value']))
                    
                    # Method 2: Direct text fields
                    if not response_content and isinstance(response_obj, dict):
                        for key in ['text', 'content', 'message', 'data', 'markdown']:
                            if key in response_obj and response_obj[key]:
                                if isinstance(response_obj[key], str):
                                    response_content.append(response_obj[key])
                    
                    # Method 3: Recursive extraction for deeply nested content
                    if not response_content:
                        extracted = extract_text_recursive(response_obj)
                        if extracted:
                            response_content = extracted
                    
                    # Add the response
                    if response_content:
                        msg = {"role": "assistant", "content": "\n".join(response_content)}
                        # Add per-message timestamp if available
                        if has_extension_data and timestamp_index < len(extension_timestamps[session_id]):
                            ts_data = extension_timestamps[session_id][timestamp_index]
                            if ts_data['role'] == 'assistant':
                                msg["timestamp"] = ts_data['timestamp']
                                timestamp_index += 1
                        messages.append(msg)
                    else:
                        # Debug: save unparseable structure
                        if debug:
                            unparseable_responses.append({
                                'session': session_id,
                                'request_index': req_idx,
                                'response_obj': response_obj
                            })
                        
                        # Keep placeholder
                        messages.append({
                            "role": "assistant",
                            "content": "[Complex response - content parsing incomplete]"
                        })
            
            # Save debug info if enabled
            if debug and unparseable_responses:
                debug_file = output_path / f"_debug_{session_id[:8]}.json"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    json.dump(unparseable_responses, f, indent=2)
            
            if messages:
                conversations.append({
                    "conversation_id": session_id,
                    "conversation_title": title if title else generate_title_precis(messages),
                    "create_time": creation_date / 1000 if creation_date else 0,
                    "messages": messages,
                    "has_per_message_timestamps": has_extension_data
                })
        
        except Exception as e:
            print(f"  [!] Could not parse {session_file.name}: {e}")
    
    # Sort chronologically
    conversations.sort(key=lambda c: c['create_time'])
    
    # Export each conversation as numbered markdown file
    exported_count = 0
    skipped_count = 0
    
    for i, conv in enumerate(conversations, 1):
        title_precis = generate_title_precis(conv['messages'])
        base_filename = f"{i:03d}_{title_precis}.md"
        file_path = output_path / base_filename
        
        # Check for existing files with same number prefix
        existing_files = list(output_path.glob(f"{i:03d}_*.md"))
        
        if existing_files:
            if conflict_mode == 'overwrite':
                # Overwrite the first existing file with this number
                file_path = existing_files[0]
                action = "↻"
            elif conflict_mode == 'suffix':
                # Find next available suffix
                suffix = 1
                while file_path.exists():
                    name_parts = base_filename.rsplit('.md', 1)
                    file_path = output_path / f"{name_parts[0]}_{suffix}.md"
                    suffix += 1
                action = "+"
            else:  # skip
                print(f"  ⊘ Skipped {base_filename} (already exists)")
                skipped_count += 1
                continue
        else:
            action = "✓"
        
        try:
            export_chat_to_markdown(conv, file_path)
            print(f"  {action} {file_path.name}")
            exported_count += 1
        except Exception as e:
            print(f"  ✗ Failed to export {file_path.name}: {e}")
    
    if skipped_count > 0:
        print(f"\n  ⊘ Skipped {skipped_count} existing file(s)")
    
    return exported_count, output_path

class WorkspaceChatsExporterGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VS Code Workspace Chat Exporter")
        self.geometry("900x850")
        self.bind("<Escape>", lambda e: self.quit())
        
        # Header
        header = tk.Label(self, text="📁 Export Workspace Chats → Markdown", 
                         font=("Arial", 16, "bold"))
        header.pack(pady=10)
        
        # Instructions
        instr = tk.Label(self, 
                        text="Export Copilot chats from a specific workspace to .md files in that workspace",
                        font=("Arial", 10), fg="gray")
        instr.pack(pady=5)
        
        # Workspace list frame
        list_frame = ttk.LabelFrame(self, text="Select Workspace", padding=10)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Search box and select all/none
        search_frame = tk.Frame(list_frame)
        search_frame.pack(fill="x", pady=(0, 5))
        
        tk.Label(search_frame, text="🔍 Filter:").pack(side="left", padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.filter_workspaces())
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side="left", fill="x", expand=True)
        
        tk.Button(search_frame, text="✕", command=lambda: self.search_var.set(""),
                 width=3).pack(side="left", padx=(5, 0))
        
        # Select all/none buttons
        tk.Button(search_frame, text="Select All", command=self.select_all,
                 bg="#E3F2FD", padx=8).pack(side="right", padx=2)
        tk.Button(search_frame, text="None", command=self.select_none,
                 bg="#FFEBEE", padx=8).pack(side="right", padx=2)
        
        # Treeview for workspaces
        columns = ('name', 'path', 'chats')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15, selectmode='extended')
        
        # Sort state tracking
        self.sort_column = 'name'
        self.sort_reverse = False
        
        # Configure column headings with sort handlers
        self.tree.heading('name', text='Workspace Name ▼', command=lambda: self.sort_by_column('name'))
        self.tree.heading('path', text='Path', command=lambda: self.sort_by_column('path'))
        self.tree.heading('chats', text='Chats', command=lambda: self.sort_by_column('chats'))
        
        self.tree.column('name', width=200)
        self.tree.column('path', width=500)
        self.tree.column('chats', width=80)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Options frame
        options_frame = tk.Frame(self)
        options_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(options_frame, text="Output:").pack(side="left", padx=5)
        
        self.output_var = tk.StringVar(value="workspace")
        tk.Radiobutton(options_frame, text="In Workspace (.vscode/copilot_history/)", 
                      variable=self.output_var, value="workspace").pack(side="left", padx=5)
        tk.Radiobutton(options_frame, text="Custom Directory", 
                      variable=self.output_var, value="custom").pack(side="left", padx=5)
        
        self.custom_dir_var = tk.StringVar()
        self.custom_dir_entry = tk.Entry(options_frame, textvariable=self.custom_dir_var, 
                                        width=35, state="disabled")
        self.custom_dir_entry.pack(side="left", padx=5)
        
        self.custom_dir_btn = tk.Button(options_frame, text="...", 
                                       command=self.choose_output_dir,
                                       state="disabled", width=3)
        self.custom_dir_btn.pack(side="left", padx=2)
        
        self.subdirs_var = tk.BooleanVar(value=True)
        self.subdirs_check = tk.Checkbutton(options_frame, text="to subdirs", 
                                           variable=self.subdirs_var,
                                           state="disabled")
        self.subdirs_check.pack(side="left", padx=2)
        
        self.output_var.trace('w', lambda *args: self.toggle_custom_dir())
        
        # Conflict handling frame
        conflict_frame = tk.Frame(self)
        conflict_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(conflict_frame, text="If files exist:", fg="#666").pack(side="left", padx=5)
        self.conflict_var = tk.StringVar(value="suffix")
        tk.Radiobutton(conflict_frame, text="Add numbered suffix (_1, _2, etc.)", 
                      variable=self.conflict_var, value="suffix").pack(side="left", padx=5)
        tk.Radiobutton(conflict_frame, text="Overwrite existing files", 
                      variable=self.conflict_var, value="overwrite").pack(side="left", padx=5)
        tk.Radiobutton(conflict_frame, text="Skip existing", 
                      variable=self.conflict_var, value="skip").pack(side="left", padx=5)
        
        # Debug option
        self.debug_var = tk.BooleanVar(value=False)
        tk.Checkbutton(conflict_frame, text="Debug mode (save unparseable responses)", 
                      variable=self.debug_var).pack(side="left", padx=15)
        
        # Buttons frame
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(btn_frame, text="🔄 Refresh Workspaces", 
                 command=self.load_workspaces,
                 bg="#2196F3", fg="white", padx=15, pady=8).pack(side="left", padx=5)
        
        tk.Button(btn_frame, text="💾 Export Selected", 
                 command=self.export_selected,
                 bg="#4CAF50", fg="white", 
                 font=("Arial", 11, "bold"),
                 padx=20, pady=8).pack(side="left", padx=5)
        
        tk.Button(btn_frame, text="❓ Help", 
                 command=self.show_help,
                 bg="#FFC107", fg="black", padx=15, pady=8).pack(side="left", padx=5)
        
        tk.Button(btn_frame, text="Exit", 
                 command=self.quit,
                 bg="red", fg="white", padx=15, pady=8).pack(side="right", padx=5)
        
        # Status frame
        status_frame = ttk.LabelFrame(self, text="Status", padding=10)
        status_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.status_text = tk.Text(status_frame, height=6, wrap="word", 
                                   state="disabled", bg="#f0f0f0")
        self.status_text.pack(fill="both", expand=True)
        
        status_scroll = ttk.Scrollbar(status_frame, command=self.status_text.yview)
        status_scroll.pack(side="right", fill="y")
        self.status_text.configure(yscrollcommand=status_scroll.set)
        
        # Load workspaces on startup
        self.workspaces = []
        self.after(100, self.load_workspaces)
    
    def toggle_custom_dir(self):
        if self.output_var.get() == "custom":
            self.custom_dir_entry.config(state="normal")
            self.custom_dir_btn.config(state="normal")
            self.subdirs_check.config(state="normal")
        else:
            self.custom_dir_entry.config(state="disabled")
            self.custom_dir_btn.config(state="disabled")
            self.subdirs_check.config(state="disabled")
    
    def choose_output_dir(self):
        dir_path = filedialog.askdirectory(title="Select Output Directory")
        if dir_path:
            self.custom_dir_var.set(dir_path)
            self.log(f"📁 Custom output: {dir_path}")
    
    def show_help(self):
        """Display help information"""
        help_text = """VS Code Workspace Chat Exporter - Help

📁 OUTPUT OPTIONS:

• In Workspace (.vscode/copilot_history/)
  Saves chats to each workspace's own .vscode/copilot_history/ directory.
  Preserves history when workspace directories are renamed.

• Custom Directory
  - Enter path manually OR click "..." to browse
  - "to subdirs" CHECKED (default): Creates organized subdirectories
    for each workspace (e.g., CustomDir/workspace1/, CustomDir/workspace2/)
  - "to subdirs" UNCHECKED: Places ALL files from ALL workspaces
    directly into the custom directory (flattened, may cause naming conflicts)

🔄 FILE CONFLICT HANDLING:

• Add numbered suffix: Creates file_1.md, file_2.md, etc.
• Overwrite existing: Replaces existing files with same number
• Skip existing: Leaves existing files unchanged

🔍 WORKSPACE SELECTION:

• Filter: Search by workspace name or path
• Select All / None: Bulk selection controls
• Multi-select: Ctrl+click or Shift+click to select multiple
• Sort: Click column headers to sort by Name, Path, or Chat count

🐛 DEBUG MODE:

Saves unparseable response structures to _debug_*.json files
for troubleshooting export issues.

⏱️ ENHANCED TIMESTAMPS:

If chaits-tracker extension is installed, per-message timestamps
are automatically loaded and included in exports.
"""
        messagebox.showinfo("Help - Workspace Chat Exporter", help_text)
    
    def select_all(self):
        """Select all visible items in the tree"""
        for item in self.tree.get_children():
            self.tree.selection_add(item)
    
    def select_none(self):
        """Deselect all items"""
        self.tree.selection_remove(*self.tree.selection())
    
    def sort_by_column(self, col):
        """Sort treeview by column"""
        # Toggle sort direction if clicking same column
        if self.sort_column == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = col
            self.sort_reverse = False
        
        # Update column headings to show sort direction
        arrow = ' ▼' if not self.sort_reverse else ' ▲'
        self.tree.heading('name', text='Workspace Name' + (arrow if col == 'name' else ''))
        self.tree.heading('path', text='Path' + (arrow if col == 'path' else ''))
        self.tree.heading('chats', text='Chats' + (arrow if col == 'chats' else ''))
        
        # Sort workspaces
        if col == 'name':
            self.workspaces.sort(key=lambda ws: ws['name'].lower(), reverse=self.sort_reverse)
        elif col == 'path':
            self.workspaces.sort(key=lambda ws: (ws['path'] or '').lower(), reverse=self.sort_reverse)
        elif col == 'chats':
            self.workspaces.sort(key=lambda ws: ws['chat_count'], reverse=self.sort_reverse)
        
        # Refresh display with current filter
        self.filter_workspaces()
    
    def log(self, message):
        self.status_text.config(state="normal")
        self.status_text.insert("end", message + "\n")
        self.status_text.see("end")
        self.status_text.config(state="disabled")
        self.update()
    
    def filter_workspaces(self):
        """Filter workspace list based on search term"""
        search_term = self.search_var.get().lower()
        
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Re-populate with filtered results
        for ws in self.workspaces:
            ws_name = ws['name'].lower()
            ws_path = (ws['path'] or '').lower()
            
            if search_term in ws_name or search_term in ws_path:
                self.tree.insert('', 'end', values=(
                    ws['name'],
                    ws['path'] or '(path unknown)',
                    ws['chat_count']
                ))
    
    def load_workspaces(self):
        self.log("🔍 Scanning for workspaces with chat history...")
        
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            self.workspaces = find_workspaces_with_chats()
            
            if not self.workspaces:
                self.log("[!] No workspaces with chat history found.")
                return
            
            # Apply current sort
            self.sort_by_column(self.sort_column)
            
            self.log(f"[+] Found {len(self.workspaces)} workspace(s) with chats.\n")
        
        except Exception as e:
            self.log(f"[-] Error scanning workspaces: {e}")
    
    def export_selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select at least one workspace to export.")
            return
        
        # Get conflict mode
        conflict_mode = self.conflict_var.get()
        debug_mode = self.debug_var.get()
        
        # Collect all selected workspaces
        selected_workspaces = []
        for item in selection:
            values = self.tree.item(item, 'values')
            ws_name = values[0]
            workspace_info = next((ws for ws in self.workspaces if ws['name'] == ws_name), None)
            if workspace_info:
                selected_workspaces.append(workspace_info)
        
        if not selected_workspaces:
            messagebox.showerror("Error", "No valid workspaces found.")
            return
        
        # Check if all workspaces have paths when using workspace output mode
        if self.output_var.get() == "workspace":
            missing_paths = [ws['name'] for ws in selected_workspaces if not ws['path']]
            if missing_paths:
                messagebox.showerror("Unknown Paths", 
                                   f"Cannot export to workspace directories (path unknown):\n" + 
                                   "\n".join(f"  - {name}" for name in missing_paths) +
                                   "\n\nPlease use custom directory option.")
                return
        
        # Determine output directory and subdirs flag
        output_dir = None
        use_subdirs = False
        if self.output_var.get() == "custom":
            output_dir = self.custom_dir_var.get().strip()
            if not output_dir:
                messagebox.showwarning("No Directory", "Please enter or choose a custom output directory.")
                return
            use_subdirs = self.subdirs_var.get()
        
        # Export in background thread
        def export_thread():
            try:
                total_exported = 0
                
                for idx, workspace_info in enumerate(selected_workspaces, 1):
                    ws_name = workspace_info['name']
                    self.log(f"\n[{idx}/{len(selected_workspaces)}] 📤 Exporting: {ws_name}")
                    self.log(f"   Storage: {workspace_info['hash'][:16]}...")
                    
                    count, output_path = export_workspace_chats_to_md(
                        workspace_info, output_dir, debug=debug_mode, conflict_mode=conflict_mode, use_subdirs=use_subdirs
                    )
                    
                    self.log(f"   [+] {count} chats → {output_path}")
                    total_exported += count
                
                self.log(f"\n++ Complete! Total: {total_exported} chats from {len(selected_workspaces)} workspace(s)")
                
                if debug_mode:
                    self.log(f"\n🐛 Debug mode: Check _debug_*.json files for unparseable responses")
                
                messagebox.showinfo("Export Complete", 
                                  f"Exported {total_exported} total chats\n"
                                  f"from {len(selected_workspaces)} workspace(s)\n\n"
                                  f"Files saved to: {'custom directory' if output_dir else 'workspace directories'}")
            
            except Exception as e:
                self.log(f"\n[-] Export failed: {e}")
                messagebox.showerror("Export Error", str(e))
        
        threading.Thread(target=export_thread, daemon=True).start()

def main():
    parser = argparse.ArgumentParser(
        description='Export VS Code Copilot chats for a specific workspace to Markdown files'
    )
    parser.add_argument('--list', action='store_true',
                       help='List all workspaces with chat history')
    parser.add_argument('--workspace', '-w',
                       help='Path to workspace directory to export')
    parser.add_argument('--current', action='store_true',
                       help='Export for current workspace (auto-detect from cwd)')
    parser.add_argument('--output', '-o',
                       help='Custom output directory (defaults to workspace/.vscode/copilot_history)')
    args = parser.parse_args()
    
    if args.list:
        # List mode
        print("[+] Workspaces with Copilot chat history:\n")
        workspaces = find_workspaces_with_chats()
        
        if not workspaces:
            print("[!] No workspaces with chat history found.")
            return
        
        for i, ws in enumerate(workspaces, 1):
            print(f"{i}. {ws['name']}")
            print(f"   Path: {ws['path'] or '(unknown)'}")
            print(f"   Chats: {ws['chat_count']}")
            print(f"   Hash: {ws['hash']}")
            print()
    
    elif args.workspace or args.current:
        # Export specific workspace
        target_path = args.workspace or str(Path.cwd())
        target_path = str(Path(target_path).resolve())
        
        print(f"🔍 Looking for workspace: {target_path}")
        
        workspaces = find_workspaces_with_chats()
        workspace_info = next((ws for ws in workspaces if ws['path'] == target_path), None)
        
        if not workspace_info:
            print(f"[-] No chat history found for workspace: {target_path}")
            print(f"\nAvailable workspaces:")
            for ws in workspaces:
                print(f"  - {ws['path']}")
            return
        
        print(f"[+] Found workspace: {workspace_info['name']}")
        print(f"  Chats: {workspace_info['chat_count']}\n")
        
        count, output_path = export_workspace_chats_to_md(workspace_info, args.output)
        
        print(f"\n[+] Exported {count} chats to: {output_path}")
    
    else:
        # GUI mode (default)
        app = WorkspaceChatsExporterGUI()
        app.mainloop()

if __name__ == '__main__':
    main()
