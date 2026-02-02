#
# NOT currently any maintained official Perplexity Chat API for *exporting chat history* [20260202].
# 

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
import json
import os
from datetime import datetime
from pathlib import Path

APP_TITLE = "Perplexity Chat Exporter"
BASE_DIR = Path(__file__).resolve().parent
ACCOUNTS_FILE = BASE_DIR / "perplexity_accounts.json"


# ---------------------------
# Storage helpers
# ---------------------------
def load_accounts():
    if ACCOUNTS_FILE.exists():
        with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_accounts(accounts):
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(accounts, f, indent=2)


# ---------------------------
# API helper
# ---------------------------
class PerplexityClient:

    def __init__(self, api_key, base_url, list_path="/chats", detail_path="/chats/{id}"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.list_path = list_path
        self.detail_path = detail_path

    def headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    # ---- CHAT LIST ----
    def list_chats(self):
        """
        Adjust endpoint if needed.
        """
        url = f"{self.base_url}{self.list_path}"
        r = requests.get(url, headers=self.headers(), timeout=30)
        r.raise_for_status()
        return r.json()

    # ---- CHAT DETAILS ----
    def get_chat(self, chat_id):
        path = self.detail_path.replace("{id}", str(chat_id))
        url = f"{self.base_url}{path}"
        r = requests.get(url, headers=self.headers(), timeout=30)
        r.raise_for_status()
        return r.json()


# ---------------------------
# GUI
# ---------------------------
class App:

    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.accounts = load_accounts()
        self.export_dir = tk.StringVar()
        self.selected_account = tk.StringVar()
        self.date_from = tk.StringVar()
        self.date_to = tk.StringVar()

        self.build_ui()
        self.refresh_accounts()

    # ---------------------------
    # UI
    # ---------------------------
    def build_ui(self):

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True)

        self.tab_export = ttk.Frame(notebook)
        self.tab_accounts = ttk.Frame(notebook)
        self.tab_help = ttk.Frame(notebook)

        notebook.add(self.tab_export, text="Export")
        notebook.add(self.tab_accounts, text="Accounts")
        notebook.add(self.tab_help, text="Help")

        self.build_export_tab()
        self.build_accounts_tab()
        self.build_help_tab()

    # ---------------------------
    # Export tab
    # ---------------------------
    def build_export_tab(self):

        frame = self.tab_export

        ttk.Label(frame, text="Select Account").pack(anchor="w", padx=10, pady=5)

        self.account_combo = ttk.Combobox(
            frame,
            textvariable=self.selected_account,
            state="readonly"
        )
        self.account_combo.pack(fill="x", padx=10)
        self.account_combo.bind("<<ComboboxSelected>>", self.on_account_selected)

        ttk.Label(frame, text="Export Directory").pack(anchor="w", padx=10, pady=5)

        dir_frame = ttk.Frame(frame)
        dir_frame.pack(fill="x", padx=10)

        ttk.Entry(dir_frame, textvariable=self.export_dir).pack(
            side="left", fill="x", expand=True
        )

        ttk.Button(dir_frame, text="Browse", command=self.choose_dir).pack(side="left")

        ttk.Label(frame, text="Date Filter (optional)").pack(anchor="w", padx=10, pady=(10, 0))

        date_frame = ttk.Frame(frame)
        date_frame.pack(fill="x", padx=10, pady=(0, 5))

        ttk.Label(date_frame, text="From (YYYY-MM-DD)").pack(side="left")
        ttk.Entry(date_frame, textvariable=self.date_from, width=14).pack(side="left", padx=(5, 15))

        ttk.Label(date_frame, text="To (YYYY-MM-DD)").pack(side="left")
        ttk.Entry(date_frame, textvariable=self.date_to, width=14).pack(side="left", padx=5)

        action_frame = ttk.Frame(frame)
        action_frame.pack(pady=10)

        tk.Button(
            action_frame,
            text="Export Chats",
            command=self.export_chats,
            bg="#2e7d32",
            fg="white",
            activebackground="#1b5e20",
            activeforeground="white",
            padx=12,
            pady=4
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            action_frame,
            text="Close",
            command=self.root.destroy,
            bg="#c62828",
            fg="white",
            activebackground="#8e0000",
            activeforeground="white",
            padx=12,
            pady=4
        ).pack(side="left")

        self.status = tk.Text(frame, height=10)
        self.status.pack(fill="both", expand=True, padx=10, pady=10)

    # ---------------------------
    # Accounts tab
    # ---------------------------
    def build_accounts_tab(self):

        frame = self.tab_accounts

        self.acc_name = tk.StringVar()
        self.acc_key = tk.StringVar()
        self.acc_url = tk.StringVar(value="https://api.perplexity.ai")
        self.acc_list_path = tk.StringVar(value="/chats")
        self.acc_detail_path = tk.StringVar(value="/chats/{id}")

        ttk.Label(frame, text="Account Name").pack(anchor="w", padx=10)
        ttk.Entry(frame, textvariable=self.acc_name).pack(fill="x", padx=10)

        ttk.Label(frame, text="API Key").pack(anchor="w", padx=10, pady=(10, 0))
        ttk.Entry(frame, textvariable=self.acc_key, show="*").pack(fill="x", padx=10)

        ttk.Label(frame, text="Base API URL").pack(anchor="w", padx=10, pady=(10, 0))
        ttk.Entry(frame, textvariable=self.acc_url).pack(fill="x", padx=10)

        ttk.Label(frame, text="Chat List Path").pack(anchor="w", padx=10, pady=(10, 0))
        ttk.Entry(frame, textvariable=self.acc_list_path).pack(fill="x", padx=10)

        ttk.Label(frame, text="Chat Detail Path (use {id})").pack(anchor="w", padx=10, pady=(10, 0))
        ttk.Entry(frame, textvariable=self.acc_detail_path).pack(fill="x", padx=10)

        ttk.Button(frame, text="Add / Update Account", command=self.add_account).pack(pady=10)
        ttk.Button(frame, text="Delete Account", command=self.delete_account).pack()

        self.acc_list = tk.Listbox(frame)
        self.acc_list.pack(fill="both", expand=True, padx=10, pady=10)
        self.acc_list.bind("<<ListboxSelect>>", self.load_account_into_fields)

    # ---------------------------
    # Help tab
    # ---------------------------
    def build_help_tab(self):

        text = tk.Text(self.tab_help, wrap="word")
        text.pack(fill="both", expand=True)

        help_text = """
HOW TO OBTAIN A PERPLEXITY API KEY

1. Sign in to Perplexity
   https://www.perplexity.ai

2. Navigate to developer / API section
   https://www.perplexity.ai/settings/api

3. Create a new API key.

4. Copy the key and paste into the Accounts tab.

NOTES:

• Some Perplexity deployments do NOT expose chat history.
• If export fails, verify endpoints:
      /chats
      /chats/{id}
• The async API endpoint
    https://docs.perplexity.ai/api-reference/async-chat-completions-get
  is NOT a chat history export. It lists async job metadata only, not
  your interactive chat/thread history.

• You can adjust the Base URL if Perplexity changes endpoints.

SECURITY:

API keys are stored locally in:
    perplexity_accounts.json

Do not share this file.

USAGE COST:

If your plan charges USD $5 per 1,000 requests, note that exporting chats
uses 1 request for the chat list plus 1 request per chat to download details.
Estimated cost per full export:
    requests = 1 + number_of_chats
    cost_usd = requests * 0.005

Example: 200 chats → 201 requests → about $1.01 per full export.
"""
        text.insert("1.0", help_text)
        text.configure(state="disabled")

    # ---------------------------
    # Account logic
    # ---------------------------
    def refresh_accounts(self):
        names = list(self.accounts.keys())
        self.account_combo["values"] = names

        self.acc_list.delete(0, tk.END)
        for name in names:
            self.acc_list.insert(tk.END, name)

        if names and not self.selected_account.get():
            self.selected_account.set(names[0])
            self.set_default_export_dir(names[0])

    def add_account(self):
        name = self.acc_name.get().strip()
        key = self.acc_key.get().strip()
        url = self.acc_url.get().strip()

        if not name or not key:
            messagebox.showerror("Error", "Name and API key required")
            return

        self.accounts[name] = {
            "api_key": key,
            "base_url": url,
            "list_path": self.acc_list_path.get().strip() or "/chats",
            "detail_path": self.acc_detail_path.get().strip() or "/chats/{id}"
        }

        save_accounts(self.accounts)
        self.refresh_accounts()
        self.set_default_export_dir(name)

    def delete_account(self):
        sel = self.acc_list.curselection()
        if not sel:
            return

        name = self.acc_list.get(sel[0])
        del self.accounts[name]
        save_accounts(self.accounts)
        self.refresh_accounts()

    def load_account_into_fields(self, event):
        sel = self.acc_list.curselection()
        if not sel:
            return

        name = self.acc_list.get(sel[0])
        acc = self.accounts[name]

        self.acc_name.set(name)
        self.acc_key.set(acc["api_key"])
        self.acc_url.set(acc["base_url"])
        self.acc_list_path.set(acc.get("list_path", "/chats"))
        self.acc_detail_path.set(acc.get("detail_path", "/chats/{id}"))
        self.selected_account.set(name)
        self.set_default_export_dir(name)

    def on_account_selected(self, event):
        name = self.selected_account.get()
        if name:
            self.set_default_export_dir(name)

    def set_default_export_dir(self, account_name):
        export_dir = BASE_DIR / account_name / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.set(str(export_dir))

    # ---------------------------
    # Export logic
    # ---------------------------
    def choose_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.export_dir.set(path)

    def log(self, msg):
        self.status.insert(tk.END, msg + "\n")
        self.status.see(tk.END)
        self.root.update()

    def parse_date_input(self, value):
        value = value.strip()
        if not value:
            return None
        return datetime.strptime(value, "%Y-%m-%d")

    def extract_chat_timestamp(self, chat):
        keys = [
            "updated_at", "created_at", "update_time", "create_time",
            "updatedAt", "createdAt", "timestamp", "time"
        ]
        for key in keys:
            if key in chat and chat[key]:
                ts = chat[key]
                if isinstance(ts, (int, float)):
                    if ts > 1e12:
                        ts = ts / 1000
                    return datetime.fromtimestamp(ts)
                if isinstance(ts, str):
                    try:
                        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    except Exception:
                        pass
        return None

    def export_chats(self):

        name = self.selected_account.get()
        if name not in self.accounts:
            messagebox.showerror("Error", "Select account")
            return

        out_dir = self.export_dir.get()
        if not out_dir:
            self.set_default_export_dir(name)
            out_dir = self.export_dir.get()

        acc = self.accounts[name]
        client = PerplexityClient(
            acc["api_key"],
            acc["base_url"],
            acc.get("list_path", "/chats"),
            acc.get("detail_path", "/chats/{id}")
        )

        try:
            date_from = self.parse_date_input(self.date_from.get())
            date_to = self.parse_date_input(self.date_to.get())
            if date_from and date_to and date_from > date_to:
                messagebox.showerror("Error", "Date From must be on or before Date To")
                return

            self.log("Fetching chat list...")
            chats = client.list_chats()

            if isinstance(chats, dict):
                chats = chats.get("data", [])

            if not chats:
                self.log("No chats returned. This endpoint may not expose chat history.")

            for chat in chats:
                chat_id = chat.get("id")
                if not chat_id:
                    continue

                chat_ts = self.extract_chat_timestamp(chat)
                if chat_ts:
                    if date_from and chat_ts < date_from:
                        continue
                    if date_to and chat_ts > date_to:
                        continue

                self.log(f"Downloading chat {chat_id}")

                chat_data = client.get_chat(chat_id)

                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{chat_id}_{ts}.json"
                filepath = os.path.join(out_dir, filename)

                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(chat_data, f, indent=2)

            self.log("Export completed!")

        except Exception as e:
            messagebox.showerror("Export Error", str(e))


# ---------------------------
# Main
# ---------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("700x500")
    App(root)
    root.mainloop()
