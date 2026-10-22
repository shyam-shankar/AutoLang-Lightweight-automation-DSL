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

        editor_frame = tk.Frame(paned, bg=self.bg_dark)
        paned.add(editor_frame, minsize=200, height=420)

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
