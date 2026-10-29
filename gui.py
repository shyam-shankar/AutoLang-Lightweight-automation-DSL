import sys
import os
import json
import shutil
import tempfile
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

from tokeniser import tokenize_code
from parser import parse
from main_engine import execute
from compile import RUNTIME_CODE

COMMANDS_CATALOG = [
    {
        "category": "🌐 Web",
        "name": "OPEN",
        "syntax": 'OPEN "<url>"',
        "desc": "Launches the default system web browser to the given URL.",
        "example": 'OPEN "https://mail.google.com"',
        "tip": "Always follow with a GAP command (e.g. GAP 5) so the webpage has time to load."
    },
    {
        "category": "🌐 Web",
        "name": "GAP / SLEEP",
        "syntax": "GAP <seconds>",
        "desc": "Pauses script execution for N seconds to allow windows or pages to render.",
        "example": "GAP 3",
        "tip": "Websites take time to open. Use GAP 3 to GAP 8 after opening links."
    },
    {
        "category": "⌨️ Keyboard",
        "name": "TYPE",
        "syntax": 'TYPE "<text>"',
        "desc": "Types text character-by-character into whatever input box is currently in focus.",
        "example": 'TYPE "Hello, quarterly report attached below."',
        "tip": "Text must be enclosed in double quotes. Keystroke interval is 30ms."
    },
    {
        "category": "⌨️ Keyboard",
        "name": "PRESS",
        "syntax": "PRESS <KEY> [count]",
        "desc": "Actuates a single keyboard key once, or repeats it N times in sequence.",
        "example": "PRESS ENTER\nPRESS TAB 4",
        "tip": "PRESS TAB 4 is great for moving down four fields in online forms."
    },
    {
        "category": "⌨️ Keyboard",
        "name": "HOTKEY",
        "syntax": "HOTKEY <KEY1> <KEY2>...",
        "desc": "Fires simultaneous keyboard combination shortcuts.",
        "example": "HOTKEY CTRL V\nHOTKEY CTRL A\nHOTKEY ALT F4",
        "tip": "Supports modifiers: CTRL, ALT, SHIFT, WIN."
    },
    {
        "category": "⌨️ Keyboard",
        "name": "TYPEFILE",
        "syntax": 'TYPEFILE "<filepath>"',
        "desc": "Reads a text file line-by-line and types each line automatically, pressing Enter after each.",
        "example": 'TYPEFILE "D:\\MATERIALS\\emails.txt"',
        "tip": "Ideal for automatically filling email recipient lists or bulk IDs."
    },
    {
        "category": "🖱️ Mouse",
        "name": "CLICK",
        "syntax": "CLICK [LEFT|RIGHT]",
        "desc": "Simulates a mouse button click at the current cursor coordinates.",
        "example": "CLICK\nCLICK RIGHT",
        "tip": "Defaults to Left Click. Use CLICK RIGHT to open context menus."
    },
    {
        "category": "🖱️ Mouse",
        "name": "FIND",
        "syntax": 'FIND "<image_path.png>"',
        "desc": "Uses OpenCV computer vision to find an image on your screen and centers the cursor over it.",
        "example": 'FIND "assets\\attach_btn.png"\nGAP 1\nCLICK',
        "tip": "Automatically polls up to 10 attempts (1/sec) with an 80% confidence threshold."
    },
    {
        "category": "🖱️ Mouse",
        "name": "SCROLL",
        "syntax": "SCROLL UP|DOWN [amount]",
        "desc": "Scrolls the active window viewport vertically by the specified amount.",
        "example": "SCROLL DOWN 5\nSCROLL UP 3",
        "tip": "Useful for navigating search result pages or long documents."
    },
    {
        "category": "🖱️ Mouse",
        "name": "COPYFILES",
        "syntax": 'COPYFILES "<folder>" ["exclude_file"]',
        "desc": "Stages files directly onto the Windows clipboard in the background using Win32 CF_HDROP memory.",
        "example": 'COPYFILES "D:\\MATERIALS" "emails.txt"',
        "tip": "Allows instant pasting (HOTKEY CTRL V) into file dialogs without opening File Explorer!"
    },
    {
        "category": "🔄 Loops",
        "name": "LOOP",
        "syntax": "LOOP <count> { ... }",
        "desc": "Repeats all enclosed commands N times. Supports nested loops.",
        "example": "LOOP 3 {\n    PRESS TAB\n    GAP 1\n}",
        "tip": "Opening brace '{' and closing brace '}' must be on separate lines."
    },
    {
        "category": "🔄 Loops",
        "name": "ALERT",
        "syntax": 'ALERT "<message>"',
        "desc": "Displays a Windows popup modal dialog with an OK button, pausing script until clicked.",
        "example": 'ALERT "Workflow completed successfully!"',
        "tip": "Great for notifying you when a long automation completes."
    },
    {
        "category": "🔄 Loops",
        "name": "WAIT",
        "syntax": "WAIT",
        "desc": "Pauses execution and waits for the user to press Enter in the terminal console.",
        "example": "WAIT",
        "tip": "Use for checkpoints where you want manual inspection before proceeding."
    },
    {
        "category": "🔄 Loops",
        "name": "SCREENSHOT",
        "syntax": 'SCREENSHOT ["filename.png"]',
        "desc": "Captures the entire screen display and saves it as a PNG image.",
        "example": 'SCREENSHOT "report_success.png"',
        "tip": "Defaults to 'screenshot.png' if filename argument is omitted."
    }
]


class ConsoleRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        self.text_widget.configure(state="normal")
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)
        self.text_widget.configure(state="disabled")

    def flush(self):
        pass


class AutomationStudio:
    def __init__(self, root):
        self.root = root
        self.root.title("Automation DSL Studio")
        self.root.geometry("980x720")
        self.root.minsize(700, 500)

        self.is_busy = False
        self.current_file = None

        self._apply_style()
        self._build_ui()
        self._load_default_content()

    def _apply_style(self):
        self.bg_dark = "#1e1e1e"
        self.bg_panel = "#252526"
        self.bg_toolbar = "#2d2d2d"
        self.fg_light = "#d4d4d4"
        self.btn_run_bg = "#2ea043"
        self.btn_build_bg = "#0078d4"
        self.btn_fg = "#ffffff"
        self.font_code = ("Consolas", 11)
        self.font_ui = ("Segoe UI", 9)
        self.font_btn = ("Segoe UI", 10, "bold")

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TNotebook", background=self.bg_toolbar, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background="#333333",
            foreground="#aaaaaa",
            padding=[16, 6],
            font=("Segoe UI", 9, "bold"),
            borderwidth=0
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.bg_dark), ("active", "#3c3c3c")],
            foreground=[("selected", "#58a6ff"), ("active", "#ffffff")]
        )

        self.root.configure(bg=self.bg_dark)

    def _build_ui(self):
        toolbar = tk.Frame(self.root, bg=self.bg_toolbar, padx=10, pady=8)
        toolbar.pack(fill=tk.X, side=tk.TOP)

        self.btn_open = tk.Button(
            toolbar, text="Open File", font=self.font_ui, bg="#3c3c3c", fg=self.fg_light,
            activebackground="#505050", activeforeground="#ffffff", relief=tk.FLAT,
            padx=12, pady=4, command=self._on_open_file
        )
        self.btn_open.pack(side=tk.LEFT, padx=3)

        self.btn_save = tk.Button(
            toolbar, text="Save File", font=self.font_ui, bg="#3c3c3c", fg=self.fg_light,
            activebackground="#505050", activeforeground="#ffffff", relief=tk.FLAT,
            padx=12, pady=4, command=self._on_save_file
        )
        self.btn_save.pack(side=tk.LEFT, padx=3)

        self.btn_clear_editor = tk.Button(
            toolbar, text="Clear Editor", font=self.font_ui, bg="#3c3c3c", fg=self.fg_light,
            activebackground="#505050", activeforeground="#ffffff", relief=tk.FLAT,
            padx=12, pady=4, command=self._on_clear_editor
        )
        self.btn_clear_editor.pack(side=tk.LEFT, padx=3)

        separator = tk.Frame(toolbar, width=2, bg="#555555", height=24)
        separator.pack(side=tk.LEFT, padx=10)

        self.btn_run = tk.Button(
            toolbar, text="▶  Run Script", font=self.font_btn, bg=self.btn_run_bg, fg=self.btn_fg,
            activebackground="#3fb950", activeforeground="#ffffff", relief=tk.FLAT,
            padx=16, pady=4, cursor="hand2", command=self._on_run
        )
        self.btn_run.pack(side=tk.LEFT, padx=5)

        self.btn_build = tk.Button(
            toolbar, text="🔨  Build .EXE", font=self.font_btn, bg=self.btn_build_bg, fg=self.btn_fg,
            activebackground="#106ebe", activeforeground="#ffffff", relief=tk.FLAT,
            padx=16, pady=4, cursor="hand2", command=self._on_build
        )
        self.btn_build.pack(side=tk.LEFT, padx=5)

        self.lbl_file = tk.Label(
            toolbar, text="No file opened", font=self.font_ui, bg=self.bg_toolbar, fg="#888888"
        )
        self.lbl_file.pack(side=tk.RIGHT, padx=10)

        paned = tk.PanedWindow(self.root, orient=tk.VERTICAL, bg="#333333", sashwidth=4)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 4))

        self.notebook = ttk.Notebook(paned)
        paned.add(self.notebook, minsize=220, height=430)

        # Tab 1: Script Editor
        editor_frame = tk.Frame(self.notebook, bg=self.bg_dark)
        self.notebook.add(editor_frame, text="  📝  Script Editor  ")

        editor_header = tk.Frame(editor_frame, bg=self.bg_panel, padx=8, pady=4)
        editor_header.pack(fill=tk.X)
        tk.Label(
            editor_header, text="SCRIPT EDITOR (Automation DSL)", font=("Segoe UI", 9, "bold"),
            bg=self.bg_panel, fg="#9cdcfe"
        ).pack(side=tk.LEFT)

        self.editor = ScrolledText(
            editor_frame, font=self.font_code, bg=self.bg_dark, fg=self.fg_light,
            insertbackground="#ffffff", selectbackground="#264f78", selectforeground="#ffffff",
            undo=True, wrap="none", relief=tk.FLAT, padx=10, pady=10
        )
        self.editor.pack(fill=tk.BOTH, expand=True)

        # Tab 2: Commands & Guide
        commands_frame = tk.Frame(self.notebook, bg=self.bg_dark)
        self.notebook.add(commands_frame, text="  📖  Commands & Guide  ")
        self._build_commands_tab(commands_frame)

        log_frame = tk.Frame(paned, bg=self.bg_panel)
        paned.add(log_frame, minsize=140, height=200)

        log_header = tk.Frame(log_frame, bg=self.bg_panel, padx=8, pady=4)
        log_header.pack(fill=tk.X)
        tk.Label(
            log_header, text="OUTPUT CONSOLE / LOGS", font=("Segoe UI", 9, "bold"),
            bg=self.bg_panel, fg="#4ec9b0"
        ).pack(side=tk.LEFT)

        btn_clear_log = tk.Button(
            log_header, text="Clear Output", font=("Segoe UI", 8), bg="#3c3c3c", fg=self.fg_light,
            activebackground="#505050", activeforeground="#ffffff", relief=tk.FLAT,
            padx=8, pady=1, command=self._on_clear_log
        )
        btn_clear_log.pack(side=tk.RIGHT)

        self.console = ScrolledText(
            log_frame, font=("Consolas", 10), bg="#141414", fg="#cccccc",
            insertbackground="#ffffff", selectbackground="#264f78", relief=tk.FLAT,
            state="disabled", padx=8, pady=8
        )
        self.console.pack(fill=tk.BOTH, expand=True)

        self.status_bar = tk.Frame(self.root, bg=self.bg_panel, padx=10, pady=4)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.lbl_status = tk.Label(
            self.status_bar, text="Ready", font=self.font_ui, bg=self.bg_panel, fg="#9cdcfe"
        )
        self.lbl_status.pack(side=tk.LEFT)

        self.lbl_hint = tk.Label(
            self.status_bar, text="Tip: Slam mouse cursor into any screen corner to abort automation (Fail-Safe)",
            font=("Segoe UI", 8), bg=self.bg_panel, fg="#777777"
        )
        self.lbl_hint.pack(side=tk.RIGHT)

    def _build_commands_tab(self, parent):
        top_bar = tk.Frame(parent, bg=self.bg_panel, padx=8, pady=6)
        top_bar.pack(fill=tk.X)

        self.active_category = "All"
        filter_frame = tk.Frame(top_bar, bg=self.bg_panel)
        filter_frame.pack(side=tk.LEFT)

        categories = ["All", "🌐 Web", "⌨️ Keyboard", "🖱️ Mouse", "🔄 Loops", "💡 Tips"]
        self.cat_buttons = {}
        for cat in categories:
            btn = tk.Button(
                filter_frame, text=cat, font=("Segoe UI", 8, "bold"),
                bg="#0078d4" if cat == "All" else "#333333",
                fg="#ffffff" if cat == "All" else "#aaaaaa",
                activebackground="#106ebe", activeforeground="#ffffff",
                relief=tk.FLAT, padx=9, pady=3, cursor="hand2",
                command=lambda c=cat: self._filter_commands(c)
            )
            btn.pack(side=tk.LEFT, padx=2)
            self.cat_buttons[cat] = btn

        search_frame = tk.Frame(top_bar, bg=self.bg_panel)
        search_frame.pack(side=tk.RIGHT, padx=4)

        tk.Label(
            search_frame, text="🔍 Filter:", font=("Segoe UI", 9),
            bg=self.bg_panel, fg="#888888"
        ).pack(side=tk.LEFT, padx=3)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self._filter_commands(self.active_category))
        search_entry = tk.Entry(
            search_frame, textvariable=self.search_var, font=("Segoe UI", 9),
            bg="#1e1e1e", fg="#ffffff", insertbackground="#ffffff",
            relief=tk.FLAT, width=16
        )
        search_entry.pack(side=tk.LEFT, ipady=2)

        self.cmd_view = ScrolledText(
            parent, font=("Segoe UI", 9), bg=self.bg_dark, fg=self.fg_light,
            relief=tk.FLAT, padx=14, pady=10, wrap="word"
        )
        self.cmd_view.pack(fill=tk.BOTH, expand=True)

        self.cmd_view.tag_config("cat_header", font=("Segoe UI", 11, "bold"), foreground="#58a6ff", spacing1=10, spacing3=4)
        self.cmd_view.tag_config("cmd_name", font=("Segoe UI", 10, "bold"), foreground="#4ec9b0", spacing1=6)
        self.cmd_view.tag_config("syntax", font=("Consolas", 9, "bold"), foreground="#ce9178", background="#2a2d2e")
        self.cmd_view.tag_config("desc", font=("Segoe UI", 9), foreground="#cccccc", spacing1=2)
        self.cmd_view.tag_config("example", font=("Consolas", 9), foreground="#dcdcaa", background="#252526", lmargin1=16, lmargin2=16, spacing1=3, spacing3=4)
        self.cmd_view.tag_config("tip", font=("Segoe UI", 8, "italic"), foreground="#e5c07b", lmargin1=16, lmargin2=16)
        self.cmd_view.tag_config("danger", font=("Segoe UI", 9, "bold"), foreground="#f85149", background="#2b1517", spacing1=6, spacing3=6, lmargin1=12, lmargin2=12)
        self.cmd_view.tag_config("rule_box", font=("Segoe UI", 9), foreground="#e5c07b", background="#252219", spacing1=3, spacing3=3, lmargin1=12, lmargin2=12)

        self.cmd_view.bind("<Double-Button-1>", self._on_cmd_double_click)

        bottom_bar = tk.Frame(parent, bg=self.bg_panel, padx=10, pady=5)
        bottom_bar.pack(fill=tk.X)

        tk.Label(
            bottom_bar, text="💡 Tip: Double-click any example to insert it into your code editor.",
            font=("Segoe UI", 8), bg=self.bg_panel, fg="#888888"
        ).pack(side=tk.LEFT)

        btn_insert = tk.Button(
            bottom_bar, text="📋 Insert Selected to Editor", font=("Segoe UI", 8, "bold"),
            bg="#2ea043", fg="#ffffff", activebackground="#3fb950", activeforeground="#ffffff",
            relief=tk.FLAT, padx=10, pady=3, cursor="hand2", command=self._insert_selected_to_editor
        )
        btn_insert.pack(side=tk.RIGHT, padx=4)

        btn_goto_editor = tk.Button(
            bottom_bar, text="📝 Go to Editor", font=("Segoe UI", 8),
            bg="#3c3c3c", fg=self.fg_light, activebackground="#505050", activeforeground="#ffffff",
            relief=tk.FLAT, padx=8, pady=3, cursor="hand2",
            command=lambda: self.notebook.select(0)
        )
        btn_goto_editor.pack(side=tk.RIGHT, padx=4)

        self._render_commands()

    def _filter_commands(self, category):
        self.active_category = category
        for cat, btn in self.cat_buttons.items():
            if cat == category:
                btn.config(bg="#0078d4", fg="#ffffff")
            else:
                btn.config(bg="#333333", fg="#aaaaaa")
        self._render_commands()

    def _render_commands(self):
        query = self.search_var.get().strip().lower()
        self.cmd_view.configure(state="normal")
        self.cmd_view.delete("1.0", tk.END)

        if self.active_category in ("All", "💡 Tips") and not query:
            self.cmd_view.insert(tk.END, "  🚨 EMERGENCY PANIC BUTTON (Safety First!)\n", "danger")
            self.cmd_view.insert(
                tk.END,
                "  If your script ever goes wild, slam your physical mouse cursor into the very\n"
                "  top-left corner of your monitor (0, 0). AutoLang will immediately abort execution!\n\n",
                "danger"
            )

        displayed_count = 0
        current_cat = None

        if self.active_category != "💡 Tips":
            for item in COMMANDS_CATALOG:
                if self.active_category != "All" and item["category"] != self.active_category:
                    continue

                if query:
                    match_text = f"{item['name']} {item['syntax']} {item['desc']} {item['example']}".lower()
                    if query not in match_text:
                        continue

                if item["category"] != current_cat and self.active_category == "All":
                    current_cat = item["category"]
                    self.cmd_view.insert(tk.END, f"\n━━━ {current_cat} ━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n", "cat_header")

                self.cmd_view.insert(tk.END, f"▸ {item['name']}  ", "cmd_name")
                self.cmd_view.insert(tk.END, f" {item['syntax']} \n", "syntax")
                self.cmd_view.insert(tk.END, f"  {item['desc']}\n", "desc")
                self.cmd_view.insert(tk.END, f"{item['example']}\n", "example")
                if item.get("tip"):
                    self.cmd_view.insert(tk.END, f"  💡 Note: {item['tip']}\n", "tip")
                self.cmd_view.insert(tk.END, "\n")
                displayed_count += 1

        if (self.active_category in ("All", "💡 Tips") and (not query or "tip" in query or "key" in query or "rule" in query)):
            self.cmd_view.insert(tk.END, "\n━━━ 💡 ESSENTIAL RULES & KEYBOARD KEYS ━━━━━━━━━━━━━━━━\n", "cat_header")
            
            tips_text = (
                "  • Double Quotes: Every web URL, file path, image name, and text string MUST be in double quotes \"...\".\n"
                "  • Timing (GAP): Always add GAP 3 to GAP 8 after opening websites/apps to let them render before typing.\n"
                "  • Case-Insensitive: Commands and keys work in any case (e.g. 'PRESS ENTER', 'press enter').\n"
                "  • Comments: Start lines with '#' or '//' to add notes that AutoLang ignores.\n\n"
                "  SUPPORTED KEY NAMES (for PRESS and HOTKEY):\n"
                "  • Common: ENTER, TAB, SPACE, BACKSPACE, DELETE, ESC\n"
                "  • Modifiers: CTRL, ALT, SHIFT, WIN (Windows Key)\n"
                "  • Arrows: UP, DOWN, LEFT, RIGHT\n"
                "  • Navigation: HOME, END, PAGEUP, PAGEDOWN\n"
                "  • Function Keys: F1 through F12\n"
                "  • Alphanumeric: A through Z, 0 through 9\n"
            )
            self.cmd_view.insert(tk.END, tips_text, "rule_box")
            displayed_count += 1

        if displayed_count == 0:
            self.cmd_view.insert(tk.END, f"\n  No commands found matching '{query}'.\n", "tip")

        self.cmd_view.configure(state="disabled")

    def _insert_selected_to_editor(self):
        try:
            selected_text = self.cmd_view.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
        except tk.TclError:
            selected_text = ""

        if not selected_text:
            messagebox.showinfo("Insert to Editor", "Please highlight/select an example or command line first, then click Insert.")
            return

        self.editor.insert(tk.INSERT, selected_text + "\n")
        self.notebook.select(0)
        self._log(f"[Guide] Inserted snippet into editor.")

    def _on_cmd_double_click(self, event):
        try:
            line = self.cmd_view.get("insert linestart", "insert lineend").strip()
            if line and not line.startswith("▸") and not line.startswith("•") and not line.startswith("🚨") and not line.startswith("━"):
                self.editor.insert(tk.INSERT, line + "\n")
                self.notebook.select(0)
                self._log(f"[Guide] Inserted '{line}' into editor.")
        except Exception:
            pass

    def _load_default_content(self):
        default_file = "automation.txt"
        if os.path.exists(default_file):
            try:
                with open(default_file, "r", encoding="utf-8") as f:
                    content = f.read()
                self.editor.delete("1.0", tk.END)
                self.editor.insert(tk.END, content)
                self.current_file = os.path.abspath(default_file)
                self.lbl_file.config(text=f"Editing: {os.path.basename(default_file)}")
            except Exception:
                pass

    def _log(self, message):
        self.console.configure(state="normal")
        self.console.insert(tk.END, message + "\n")
        self.console.see(tk.END)
        self.console.configure(state="disabled")

    def _set_busy(self, busy, status_msg="Ready"):
        self.is_busy = busy
        self.lbl_status.config(text=status_msg)
        state = tk.DISABLED if busy else tk.NORMAL
        self.btn_run.config(state=state)
        self.btn_build.config(state=state)
        self.btn_open.config(state=state)
        self.btn_save.config(state=state)
        self.btn_clear_editor.config(state=state)

    def _on_clear_editor(self):
        if messagebox.askyesno("Clear Editor", "Clear all code in editor?"):
            self.editor.delete("1.0", tk.END)

    def _on_clear_log(self):
        self.console.configure(state="normal")
        self.console.delete("1.0", tk.END)
        self.console.configure(state="disabled")

    def _on_open_file(self):
        path = filedialog.askopenfilename(
            title="Open Automation Script",
            filetypes=[("Text Files (*.txt)", "*.txt"), ("All Files (*.*)", "*.*")]
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.editor.delete("1.0", tk.END)
                self.editor.insert(tk.END, content)
                self.current_file = path
                self.lbl_file.config(text=f"Editing: {os.path.basename(path)}")
                self._log(f"[File] Loaded '{path}'")
            except Exception as e:
                messagebox.showerror("Error Opening File", str(e))

    def _on_save_file(self):
        if not self.current_file:
            path = filedialog.asksaveasfilename(
                title="Save Automation Script",
                defaultextension=".txt",
                filetypes=[("Text Files (*.txt)", "*.txt"), ("All Files (*.*)", "*.*")],
                initialfile="automation.txt"
            )
            if not path:
                return
            self.current_file = path

        try:
            content = self.editor.get("1.0", tk.END)
            with open(self.current_file, "w", encoding="utf-8") as f:
                f.write(content)
            self.lbl_file.config(text=f"Editing: {os.path.basename(self.current_file)}")
            self._log(f"[File] Saved to '{self.current_file}'")
        except Exception as e:
            messagebox.showerror("Error Saving File", str(e))

    def _on_run(self):
        if self.is_busy:
            return

        code = self.editor.get("1.0", tk.END).strip()
        if not code:
            messagebox.showwarning("Empty Script", "Please enter some automation code before running.")
            return

        self._set_busy(True, "Running automation script...")
        self._log("\n" + "=" * 50)
        self._log("[RUN] Starting script execution...")

        threading.Thread(target=self._run_thread, args=(code,), daemon=True).start()

    def _run_thread(self, code):
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        redirector = ConsoleRedirector(self.console)

        try:
            sys.stdout = redirector
            sys.stderr = redirector

            print("[1/3] Tokenising...")
            tokens = tokenize_code(code)
            if not tokens:
                print("Error: No valid tokens generated.")
                return

            print("[2/3] Parsing...")
            ast = parse(tokens)
            print(f"       {len(ast)} top-level statements parsed successfully.")

            print(f"[3/3] Executing {len(ast)} statements...")
            execute(ast)

            print("\n[OK] Script finished successfully.")

        except Exception as e:
            print(f"\n[ERROR] Execution failed: {e}")
            self.root.after(0, lambda: messagebox.showerror("Execution Error", str(e)))

        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            self.root.after(0, lambda: self._set_busy(False, "Ready"))

    def _on_build(self):
        if self.is_busy:
            return

        code = self.editor.get("1.0", tk.END).strip()
        if not code:
            messagebox.showwarning("Empty Script", "Please enter some automation code before building.")
            return

        dest_path = filedialog.asksaveasfilename(
            title="Save Compiled Executable As...",
            defaultextension=".exe",
            filetypes=[("Executable Files (*.exe)", "*.exe")],
            initialfile="automation.exe"
        )
        if not dest_path:
            return

        self._set_busy(True, "Building standalone .EXE (this may take 30-60 seconds)...")
        self._log("\n" + "=" * 50)
        self._log(f"[BUILD] Starting compilation...")
        self._log(f"[BUILD] Destination: {dest_path}")

        threading.Thread(target=self._build_thread, args=(code, dest_path), daemon=True).start()

    def _build_thread(self, code, dest_path):
        build_dir = tempfile.mkdtemp(prefix="dsl_build_")
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        redirector = ConsoleRedirector(self.console)

        try:
            sys.stdout = redirector
            sys.stderr = redirector

            print("[1/4] Tokenising code...")
            tokens = tokenize_code(code)
            if not tokens:
                raise RuntimeError("No tokens generated from script.")

            print("[2/4] Parsing into AST...")
            ast = parse(tokens)
            print(f"       {len(ast)} statements parsed.")

            print("[3/4] Generating standalone Python source...")
            ast_json = json.dumps(ast, indent=2)
            gen_py = os.path.join(build_dir, "automation_compiled.py")

            generated_source = f'''{RUNTIME_CODE}

AST = {ast_json}

if __name__ == "__main__":
    print("Running compiled automation...")
    print()
    execute(AST)
    print()
    print("Done.")
    input("Press Enter to exit...")
'''
            with open(gen_py, "w", encoding="utf-8") as f:
                f.write(generated_source)

            print("[4/4] Packaging binary with PyInstaller...")
            print("       Please wait while dependencies are bundled...")

            exe_name = os.path.splitext(os.path.basename(dest_path))[0]
            dist_dir = os.path.join(build_dir, "dist")
            work_dir = os.path.join(build_dir, "work")

            proc = subprocess.Popen(
                [
                    sys.executable, "-m", "PyInstaller",
                    "--onefile",
                    "--console",
                    "--distpath", dist_dir,
                    "--workpath", work_dir,
                    "--specpath", build_dir,
                    "--name", exe_name,
                    gen_py,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            for line in proc.stdout:
                if "Building EXE" in line or "compiled successfully" in line or "INFO:" in line:
                    print(f"       {line.strip()}")

            proc.wait()

            if proc.returncode != 0:
                raise RuntimeError("PyInstaller build process failed. Check output console for details.")

            built_exe = os.path.join(dist_dir, f"{exe_name}.exe")
            if not os.path.exists(built_exe):
                raise RuntimeError(f"Expected binary '{built_exe}' not found.")

            os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
            shutil.copy2(built_exe, dest_path)

            file_size_mb = os.path.getsize(dest_path) / (1024 * 1024)
            print(f"\n[OK] Build Succeeded!")
            print(f"       Saved to: {dest_path}")
            print(f"       Size:     {file_size_mb:.1f} MB")

            self.root.after(0, lambda: messagebox.showinfo(
                "Build Succeeded",
                f"Executable created successfully!\n\nLocation:\n{dest_path}\n\nSize: {file_size_mb:.1f} MB"
            ))

        except Exception as e:
            print(f"\n[ERROR] Build failed: {e}")
            self.root.after(0, lambda: messagebox.showerror("Build Error", str(e)))

        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            shutil.rmtree(build_dir, ignore_errors=True)
            self.root.after(0, lambda: self._set_busy(False, "Ready"))


def main():
    root = tk.Tk()
    app = AutomationStudio(root)
    root.mainloop()


if __name__ == "__main__":
    main()
