"""
Export VS Code Copilot chat history to JSON format compatible with chaits.

This reads VS Code's internal storage (undocumented format) and attempts
to extract conversation data. The format may change between VS Code versions.

NOTE: VS Code stores Copilot chats in workspace-specific SQLite databases
and ephemeral session storage, NOT in a centralized conversation history.
This means chat history is fragmented across workspaces and may be lost
when workspaces are deleted.

Usage:
    python export_vscode_copilot.py                    # GUI mode
    python export_vscode_copilot.py --cli              # CLI mode
    python export_vscode_copilot.py --output file.json # Custom output
"""

import json
import os
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from datetime import datetime
import argparse
import threading

def find_vscode_copilot_data():
    """Locate VS Code Copilot data directory"""
    if os.name == 'nt':  # Windows
        base = Path(os.environ['APPDATA']) / 'Code'
    elif os.name == 'posix':
        if 'darwin' in os.sys.platform:  # Mac
            base = Path.home() / 'Library' / 'Application Support' / 'Code'
        else:  # Linux
            base = Path.home() / '.config' / 'Code'
    else:
        raise OSError("Unsupported OS")
    
    return base / 'User' / 'globalStorage' / 'github.copilot-chat'

def load_extension_timestamps():
    """
    Load per-message timestamps from chaits-tracker extension if available.
    Returns dict mapping sessionId -> list of timestamps.
    Gracefully returns empty dict if extension not installed - does not fail.
    """
    try:
        global_storage = Path(os.environ.get('APPDATA', '')) / 'Code' / 'User' / 'globalStorage' / 'chaits-tracker' / 'interaction-logs'
        
        if not global_storage.exists():
            return {}  # Extension not installed, continue without timestamps
        
        print(f"\n++ Loading timestamps from chaits-tracker extension...")
        session_timestamps = {}
        
        # Read session-specific logs
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
                                'role': interaction['role'],
                                'content': interaction.get('content', '')
                            })
                
                if timestamps:
                    session_timestamps[session_id] = timestamps
                    print(f"  + Loaded {len(timestamps)} timestamped messages for session {session_id[:8]}")
            except Exception as e:
                print(f"  [!] Could not read {session_file.name}: {e}")
        
        if session_timestamps:
            print(f"  ++ Total: {len(session_timestamps)} sessions with enhanced timestamps")
        
        return session_timestamps
    except Exception as e:
        # Silently fail - extension might not be installed
        return {}

def export_copilot_chats(output_path):
    """
    Export Copilot chats from workspaceStorage chatSessions directories.
    
    VS Code stores chat history in:
    workspaceStorage/<workspace-hash>/chatSessions/<session-uuid>.json
    
    Each session JSON contains: sessionId, customTitle, creationDate, and requests[]
    where each request has message (user) and response (assistant) content.
    
    If chaits-tracker extension is installed, loads per-message timestamps.
    """
    conversations = []
    
    # Load extension timestamps if available
    extension_timestamps = load_extension_timestamps()
    
    # Search workspace storage for chatSessions directories
    workspace_storage = Path(os.environ['APPDATA']) / 'Code' / 'User' / 'workspaceStorage'
    if not workspace_storage.exists():
        print(f"[-] Workspace storage not found: {workspace_storage}")
        return
    
    print(f"\nScanning workspace storage: {workspace_storage}")
    
    session_count = 0
    for workspace_dir in workspace_storage.iterdir():
        if not workspace_dir.is_dir():
            continue
        
        chat_sessions_dir = workspace_dir / 'chatSessions'
        if not chat_sessions_dir.exists():
            continue
        
        # Process each chat session JSON file
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
                    continue  # Skip empty sessions
                
                # Check if we have extension timestamps for this session
                has_extension_data = session_id in extension_timestamps
                timestamp_index = 0
                
                # Convert to chait format
                messages = []
                for req in requests:
                    # Extract user message
                    if 'message' in req and req['message']:
                        user_text = req['message'].get('text', '')
                        if user_text:
                            msg = {
                                "role": "user",
                                "content": user_text
                            }
                            # Add per-message timestamp if available
                            if has_extension_data and timestamp_index < len(extension_timestamps[session_id]):
                                ts_data = extension_timestamps[session_id][timestamp_index]
                                if ts_data['role'] == 'user':
                                    msg["timestamp"] = ts_data['timestamp']
                                    timestamp_index += 1
                            messages.append(msg)
                    
                    # Extract assistant response
                    # Response.value is an array of content objects
                    if 'response' in req and req['response']:
                        response_content = []
                        response_obj = req['response']
                        
                        # Extract from value array if present
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
                        
                        # Fallback: try to extract any string content
                        if not response_content and isinstance(response_obj, dict):
                            for key in ['text', 'content', 'message']:
                                if key in response_obj:
                                    response_content.append(str(response_obj[key]))
                        
                        # Add the response
                        if response_content:
                            msg = {
                                "role": "assistant",
                                "content": "\n".join(response_content)
                            }
                            # Add per-message timestamp if available
                            if has_extension_data and timestamp_index < len(extension_timestamps[session_id]):
                                ts_data = extension_timestamps[session_id][timestamp_index]
                                if ts_data['role'] == 'assistant':
                                    msg["timestamp"] = ts_data['timestamp']
                                    timestamp_index += 1
                            messages.append(msg)
                        else:
                            # Keep placeholder if we really can't parse it
                            messages.append({
                                "role": "assistant",
                                "content": "[Complex response - content parsing incomplete]"
                            })
                
                if messages:
                    conversation = {
                        "conversation_id": session_id,
                        "conversation_title": title if title else f"Chat {session_id[:8]}",
                        "create_time": creation_date / 1000 if creation_date else 0,  # ms to seconds
                        "messages": messages,
                        "has_per_message_timestamps": has_extension_data
                    }
                    conversations.append(conversation)
                    session_count += 1
                    timestamp_marker = " [time-tracked]" if has_extension_data else ""
                    print(f"  [+] Extracted: {title} ({len(messages)} messages){timestamp_marker}")
                
            except Exception as e:
                print(f"  [!] Could not parse {session_file.name}: {e}")
    
    if conversations:
        # Export in chaits-compatible format
        export_data = {
            "source": "vscode-copilot",
            "exported_at": datetime.now().isoformat(),
            "note": "Exported from VS Code workspaceStorage chatSessions",
            "conversations": conversations
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n[+] Exported {session_count} conversations to {output_path}")
    else:
        print("\n[!] No chat sessions found in workspaceStorage.")
    
    return len(conversations)

def get_chaits_export_path(account_name="default"):
    """Get the appropriate export path in chaits directory structure"""
    # Assume script is in chaits directory
    base_dir = Path(__file__).parent
    copilot_dir = base_dir / ".aiccounts" / "accounts_copilot" / account_name / "exports"
    copilot_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return copilot_dir / f"vscode_copilot_{timestamp}.json"

class CopilotExporterGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VS Code Copilot Exporter for chaits")
        self.geometry("700x600")
        self.bind("<Escape>", lambda e: self.quit())
        
        # Header
        header = tk.Label(self, text="🤖 VS Code Copilot → chaits", 
                         font=("Arial", 16, "bold"))
        header.pack(pady=10)
        
        # Tab control
        tab_control = ttk.Notebook(self)
        tab_control.pack(fill="both", expand=True, padx=10, pady=(5, 0))
        
        # Tab 1: Auto Export
        auto_tab = tk.Frame(tab_control)
        tab_control.add(auto_tab, text="🔍 Auto Scan")
        
        # Tab 2: Manual Import
        manual_tab = tk.Frame(tab_control)
        tab_control.add(manual_tab, text="Manual Import")
        
        # Setup tabs
        self.setup_auto_tab(auto_tab)
        self.setup_manual_tab(manual_tab)
    
    def setup_auto_tab(self, auto_tab):
        # === AUTO TAB ===
        tk.Label(auto_tab, text="Scan VS Code for chat history (usually empty)", 
                font=("Arial", 10, "italic"), fg="gray").pack(pady=5)
        
        # Status frame
        status_frame = ttk.LabelFrame(auto_tab, text="Scan Status", padding=10)
        status_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.status_text = tk.Text(status_frame, height=10, wrap="word", 
                                   state="disabled", bg="#f0f0f0")
        self.status_text.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(status_frame, command=self.status_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.status_text.config(yscrollcommand=scrollbar.set)
        
        # Account name
        account_frame = tk.Frame(auto_tab)
        account_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(account_frame, text="Account:").pack(side="left")
        self.account_entry = tk.Entry(account_frame, width=30)
        self.account_entry.insert(0, "default")
        self.account_entry.pack(side="left", padx=5)
        
        self.export_btn = tk.Button(account_frame, text="🔍 Scan VS Code Storage", 
                                    command=self.start_export,
                                    bg="#2196F3", fg="white",
                                    padx=10, pady=5)
        self.export_btn.pack(side="left", padx=5)
        
        # Small red exit button next to scan button
        tk.Button(account_frame, text="Exit", command=self.quit, 
                 bg="red", fg="white", padx=10, pady=5).pack(side="left", padx=5)
    
    def setup_manual_tab(self, manual_tab):
        # === MANUAL TAB ===
        tk.Label(manual_tab, text="Import copied chat text from VS Code", 
                font=("Arial", 10, "italic"), fg="gray").pack(pady=5)
        
        # Instructions
        instr_frame = ttk.LabelFrame(manual_tab, text="📋 Instructions", padding=10)
        instr_frame.pack(fill="x", padx=10, pady=5)
        
        instructions = """1. Open VS Code Chat panel
2. Select conversation text (Ctrl+A)
3. Copy (Ctrl+C)
4. Paste below
5. Add conversation title
6. Click "Save to chaits" """
        
        tk.Label(instr_frame, text=instructions, justify="left", 
                font=("Consolas", 9)).pack(anchor="w")
        
        # Conversation title
        title_frame = tk.Frame(manual_tab)
        title_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(title_frame, text="Title:").pack(side="left")
        self.title_entry = tk.Entry(title_frame, width=50)
        self.title_entry.insert(0, f"VS Code Chat {datetime.now().strftime('%Y-%m-%d')}")
        self.title_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        # Account for manual import
        manual_account_frame = tk.Frame(manual_tab)
        manual_account_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(manual_account_frame, text="Account:").pack(side="left")
        self.manual_account_entry = tk.Entry(manual_account_frame, width=30)
        self.manual_account_entry.insert(0, "default")
        self.manual_account_entry.pack(side="left", padx=5)
        
        # Text input
        text_frame = ttk.LabelFrame(manual_tab, text="Paste Chat Content", padding=10)
        text_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.chat_text = tk.Text(text_frame, height=15, wrap="word")
        self.chat_text.pack(fill="both", expand=True)
        
        text_scroll = ttk.Scrollbar(text_frame, command=self.chat_text.yview)
        text_scroll.pack(side="right", fill="y")
        self.chat_text.config(yscrollcommand=text_scroll.set)
        
        # Save button
        save_btn = tk.Button(manual_tab, text="💾 Save to chaits", 
                            command=self.save_manual_chat,
                            bg="#4CAF50", fg="white",
                            font=("Arial", 12, "bold"),
                            padx=20, pady=10)
        save_btn.pack(pady=10)
    
    def update_output_path(self):
        account = self.account_entry.get() or "default"
        path = get_chait_export_path(account)
        if hasattr(self, 'output_var'):
            self.output_var.set(str(path))
    
    def log(self, message, tag="info"):
        self.status_text.config(state="normal")
        self.status_text.insert("end", message + "\n")
        self.status_text.see("end")
        self.status_text.config(state="disabled")
        self.update()
    
    def save_manual_chat(self):
        """Save manually pasted chat to chaits format"""
        content = self.chat_text.get("1.0", "end-1c").strip()
        if not content:
            messagebox.showwarning("Empty Content", "Please paste chat content first!")
            return
        
        title = self.title_entry.get().strip() or "Untitled Conversation"
        account = self.manual_account_entry.get().strip() or "default"
        
        # Parse content into messages (simple split by common patterns)
        messages = []
        lines = content.split('\n')
        current_role = "user"
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect role changes (simple heuristic)
            if line.lower().startswith(("user:", "you:", "q:")):
                if current_content:
                    messages.append({
                        "role": current_role,
                        "content": "\n".join(current_content),
                        "create_time": datetime.now().isoformat()
                    })
                current_role = "user"
                current_content = [line.split(":", 1)[-1].strip()]
            elif line.lower().startswith(("assistant:", "copilot:", "a:", "github copilot:")):
                if current_content:
                    messages.append({
                        "role": current_role,
                        "content": "\n".join(current_content),
                        "create_time": datetime.now().isoformat()
                    })
                current_role = "assistant"
                current_content = [line.split(":", 1)[-1].strip()]
            else:
                current_content.append(line)
        
        # Add last message
        if current_content:
            messages.append({
                "role": current_role,
                "content": "\n".join(current_content),
                "create_time": datetime.now().isoformat()
            })
        
        # If no structured messages detected, treat whole content as single message
        if not messages:
            messages.append({
                "role": "user",
                "content": content,
                "create_time": datetime.now().isoformat()
            })
        
        # Create conversation in chait format
        conversation = {
            "id": f"manual_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "title": title,
            "messages": messages
        }
        
        # Save to chaits directory
        output_path = get_chaits_export_path(account)
        export_data = {
            "source": "vscode-copilot-manual",
            "exported_at": datetime.now().isoformat(),
            "conversations": [conversation]
        }
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("Saved!", 
                              f"Chat saved to:\n{output_path}\n\n"
                              f"Messages: {len(messages)}\n"
                              f"Account: {account}\n\n"
                              f"Run chaits.py to search across all chats!")
            
            # Clear inputs
            self.chat_text.delete("1.0", "end")
            self.title_entry.delete(0, "end")
            self.title_entry.insert(0, f"VS Code Chat {datetime.now().strftime('%Y-%m-%d')}")
            
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save:\n{e}")
    
    def start_export(self):
        self.export_btn.config(state="disabled", text="⏳ Scanning...")
        self.status_text.config(state="normal")
        self.status_text.delete("1.0", "end")
        self.status_text.config(state="disabled")
        
        def export_thread():
            try:
                account = self.account_entry.get().strip() or "default"
                output_path = get_chaits_export_path(account)
                
                self.log(f"🔍 Scanning VS Code storage...")
                self.log(f"[+] Account: {account}")
                self.log(f"📝 Output: {output_path}\n")
                
                # Redirect print to GUI
                import sys
                from io import StringIO
                
                old_stdout = sys.stdout
                sys.stdout = StringIO()
                
                count = export_copilot_chats(str(output_path))
                
                output = sys.stdout.getvalue()
                sys.stdout = old_stdout
                
                # Display output in GUI
                for line in output.split('\n'):
                    if line.strip():
                        self.log(line)
                
                if count > 0:
                    self.log(f"\n[+] Success! Ready to use in chaits.", "success")
                    self.log(f"   Run chaits.py to search across all conversations.")
                    messagebox.showinfo("Export Complete", 
                                      f"Exported {count} conversations to:\n{output_path}")
                else:
                    self.log(f"\n[!] No automated export possible.", "warning")
                    self.log(f"   Use 'Manual Import' tab to paste chat text.")
                    messagebox.showinfo("No Auto Data",
                                      "VS Code doesn't store persistent chat history.\n\n"
                                      "Use the 'Manual Import' tab to:\n"
                                      "1. Copy chat from VS Code\n"
                                      "2. Paste into the tool\n"
                                      "3. Save to chaits")
                
            except Exception as e:
                self.log(f"\n[-] Error: {e}", "error")
                messagebox.showerror("Export Error", str(e))
            finally:
                self.export_btn.config(state="normal", text="🔍 Scan VS Code Storage")
        
        threading.Thread(target=export_thread, daemon=True).start()


def main():
    parser = argparse.ArgumentParser(description='Export VS Code Copilot chats to chaits')
    parser.add_argument('--cli', action='store_true',
                       help='Run in CLI mode (no GUI)')
    parser.add_argument('--output', '-o',
                        help='Custom output path (CLI mode only)')
    parser.add_argument('--account', '-a', default='default',
                       help='Account name for chaits organization')
    args = parser.parse_args()
    
    if args.cli:
        # CLI mode
        if args.output:
            output_path = args.output
        else:
            output_path = get_chaits_export_path(args.account)
        
        print(f"[+] Exporting to: {output_path}")
        count = export_copilot_chats(str(output_path))
        
        if count > 0:
            print(f"\n[+] Export complete! File ready for chaits.")
            print(f"   Location: {output_path}")
    else:
        # GUI mode (default)
        app = CopilotExporterGUI()
        app.mainloop()

if __name__ == '__main__':
    main()
