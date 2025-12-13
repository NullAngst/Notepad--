import tkinter as tk
from tkinter import filedialog, messagebox, font
import os
import re
import sys
import codecs
import subprocess
import threading
import tempfile
import webbrowser
from datetime import datetime

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class NotepadMinusMinus:
    def __init__(self, root):
        self.root = root
        self.root.title("Notepad--")
        self.root.geometry("960x720")
        
        # --- THEME DEFINITIONS ---
        self.THEMES = {
            'light': {
                'bg': 'white', 'fg': 'black', 'insert': 'black',
                'line_num_bg': '#f0f0f0', 'line_num_fg': '#808080',
                'status_bar_bg': '#f0f0f0', 'status_bar_fg': 'black',
            },
            'dark': {
                'bg': '#1e1e1e', 'fg': '#d4d4d4', 'insert': '#d4d4d4', 
                'line_num_bg': '#252526', 'line_num_fg': '#6a6a6a',
                'status_bar_bg': '#252526', 'status_bar_fg': '#d4d4d4',
            }
        }

        # --- SYNTAX DEFINITIONS ---
        self.SYNTAX_RULES = {
            'python': {
                'keywords': r'\b(def|class|if|else|elif|import|from|return|for|while|in|is|not|and|or|try|except|finally|with|as|pass|lambda|global|nonlocal|True|False|None)\b',
                'comments': r'#.*$'
            },
            'c_style': { # C, C++, Java, JS, C#
                'keywords': r'\b(int|float|double|char|void|if|else|for|while|do|return|switch|case|break|continue|struct|class|public|private|protected|static|new|this|import|package|function|var|let|const|console)\b',
                'comments': r'//.*$' 
            },
            'html': {
                'keywords': r'<\/?[a-zA-Z0-9]+.*?>', # Tags
                'comments': r''
            },
            'sql': {
                'keywords': r'\b(SELECT|FROM|WHERE|INSERT|UPDATE|DELETE|CREATE|DROP|TABLE|INDEX|ALTER|JOIN|INNER|LEFT|RIGHT|ON|GROUP|BY|ORDER|ASC|DESC|LIMIT|VALUES)\b',
                'comments': r'--.*$'
            },
            'generic': {
                'keywords': r'\b(true|false|null)\b',
                'comments': r''
            }
        }
        
        # Extension mapping
        self.EXTENSIONS = {
            '.py': 'python', '.pyw': 'python',
            '.c': 'c_style', '.cpp': 'c_style', '.h': 'c_style', '.java': 'c_style', '.js': 'c_style', '.cs': 'c_style',
            '.html': 'html', '.xml': 'html',
            '.sql': 'sql'
        }
        
        self.config_dir = self._get_config_dir()
        self.config_file = os.path.join(self.config_dir, "config.json")
        
        # --- ICON SETUP ---
        self.icon_path = None
        try:
            if sys.platform.startswith('win'):
                self.icon_path = resource_path("app_icon.ico")
                if os.path.exists(self.icon_path):
                    self.root.iconbitmap(self.icon_path)
            else:
                self.icon_path = resource_path("app_icon.png") 
                if os.path.exists(self.icon_path):
                    img = tk.PhotoImage(file=self.icon_path)
                    self.root.iconphoto(True, img)
        except Exception as e:
            print(f"Icon load error: {e}")

        # --- STATE VARIABLES ---
        self.filename = "Untitled"
        self.file_path = None
        self.word_wrap = False
        self.current_lang = 'generic'
        
        self.is_dark_theme = tk.BooleanVar(value=False)
        self.show_line_numbers = tk.BooleanVar(value=False)
        self.syntax_highlighting = tk.BooleanVar(value=False)

        self._load_config()
        
        self.current_font_family = "Consolas"
        self.current_font_size = 12
        
        # --- UI LAYOUT ---
        self.status_bar = tk.Label(self.root, text="Ln 1, Col 1 | Words: 0 | Chars: 0", 
                                   bd=1, relief=tk.SUNKEN, anchor=tk.E, padx=10)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        # Scrollbars
        self.scrollbar_y = tk.Scrollbar(self.main_frame)
        self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.scrollbar_x = tk.Scrollbar(self.main_frame, orient=tk.HORIZONTAL)
        self.scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Line Number Bar
        self.line_number_bar = tk.Text(self.main_frame, width=4, padx=4, takefocus=0, 
                                       border=0, background='#f0f0f0', state='disabled', cursor="arrow")
        self.line_number_bar.pack(side=tk.LEFT, fill=tk.Y)

        # Main Text Area
        self.text_area = tk.Text(self.main_frame, undo=True, wrap=tk.NONE,
                                 selectbackground="#0078D7", 
                                 selectforeground="white",
                                 inactiveselectbackground="#0078D7",
                                 yscrollcommand=self._on_text_scroll, # Custom scroller
                                 xscrollcommand=self.scrollbar_x.set)
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        
        # Link Scrollbars
        self.scrollbar_y.config(command=self._on_scrollbar_scroll)
        self.scrollbar_x.config(command=self.text_area.xview)

        # Syntax Tags
        self.text_area.tag_config('keyword', foreground='#569cd6') 
        self.text_area.tag_config('string', foreground='#ce9178')
        self.text_area.tag_config('comment', foreground='#6a9955')

        # Bindings
        self.text_area.bind("<KeyRelease>", self._on_content_changed)
        self.text_area.bind("<ButtonRelease>", self._on_cursor_move)
        self.text_area.bind("<<Modified>>", self.on_modified)
        
        # Sync Line Number Scrolling with MouseWheel
        self.line_number_bar.bind("<MouseWheel>", self._on_mousewheel)
        self.text_area.bind("<MouseWheel>", self._on_mousewheel)

        self.apply_theme()
        self.apply_font()
        
        # Toggle line numbers visibility based on config
        self.toggle_line_numbers(init=True)

        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)
        self.create_menus()
        self.bind_shortcuts()
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        
        self.text_area.edit_modified(False)

        if len(sys.argv) > 1:
            file_to_open = sys.argv[1]
            if os.path.exists(file_to_open):
                self.load_file_content(file_to_open)

    # --------------------------------------------------------------------------
    # LOGIC: Helpers (Icon, etc)
    # --------------------------------------------------------------------------
    def _set_window_icon(self, window):
        """Helper to apply the app icon to Toplevel windows."""
        try:
            if self.icon_path and os.path.exists(self.icon_path):
                if sys.platform.startswith('win'):
                    window.iconbitmap(self.icon_path)
                else:
                    img = tk.PhotoImage(file=self.icon_path)
                    window.iconphoto(True, img)
        except Exception:
            pass

    # --------------------------------------------------------------------------
    # LOGIC: Scrolling & Line Numbers
    # --------------------------------------------------------------------------
    def _on_text_scroll(self, *args):
        self.scrollbar_y.set(*args)
        self.line_number_bar.yview_moveto(args[0])

    def _on_scrollbar_scroll(self, *args):
        self.text_area.yview(*args)
        self.line_number_bar.yview(*args)
        
    def _on_mousewheel(self, event):
        if sys.platform == "darwin":
            self.text_area.yview_scroll(int(-1*(event.delta)), "units")
            self.line_number_bar.yview_scroll(int(-1*(event.delta)), "units")
        else:
            self.text_area.yview_scroll(int(-1*(event.delta/120)), "units")
            self.line_number_bar.yview_scroll(int(-1*(event.delta/120)), "units")
        return "break"

    def _on_content_changed(self, event=None):
        self.update_line_numbers()
        self.update_status_bar()
        # Always run highlight syntax to handle updates or clearing
        self.highlight_syntax()

    def _on_cursor_move(self, event=None):
        self.update_status_bar()

    def update_line_numbers(self):
        if not self.show_line_numbers.get():
            return

        lines = self.text_area.get(1.0, tk.END).split("\n")
        line_count = len(lines)
        if lines[-1] == '': line_count -= 1 
        if line_count < 1: line_count = 1
        
        line_numbers_string = "\n".join(str(i) for i in range(1, line_count + 1))
        
        self.line_number_bar.config(state='normal')
        self.line_number_bar.delete(1.0, tk.END)
        self.line_number_bar.insert(1.0, line_numbers_string)
        self.line_number_bar.config(state='disabled')
        
        first_visible = self.text_area.yview()[0]
        self.line_number_bar.yview_moveto(first_visible)

    def toggle_line_numbers(self, init=False):
        if self.show_line_numbers.get():
            # Fix: Use 'before' to ensure it stays to the left of the text area
            self.line_number_bar.pack(side=tk.LEFT, fill=tk.Y, before=self.text_area)
            self.update_line_numbers()
        else:
            self.line_number_bar.pack_forget()

    # --------------------------------------------------------------------------
    # LOGIC: Syntax Highlighting
    # --------------------------------------------------------------------------
    def detect_language(self):
        if not self.file_path:
            self.current_lang = 'generic'
            return

        _, ext = os.path.splitext(self.file_path)
        self.current_lang = self.EXTENSIONS.get(ext.lower(), 'generic')

    def highlight_syntax(self, event=None):
        # Fix: Remove tags FIRST. 
        # If disabled, we simply return after clearing, effectively toggling it off visually.
        
        self.text_area.config(undo=False) # optimization: don't clog undo stack with highlighting

        for tag in ['keyword', 'string', 'comment']:
            self.text_area.tag_remove(tag, '1.0', tk.END)

        if not self.syntax_highlighting.get():
            self.text_area.config(undo=True)
            return

        content = self.text_area.get('1.0', tk.END)
        rules = self.SYNTAX_RULES.get(self.current_lang, self.SYNTAX_RULES['generic'])

        if 'keywords' in rules and rules['keywords']:
            for match in re.finditer(rules['keywords'], content):
                start = f"1.0 + {match.start()}c"
                end = f"1.0 + {match.end()}c"
                self.text_area.tag_add('keyword', start, end)

        strings = r'(\".*?\")|(\'.*?\')'
        for match in re.finditer(strings, content):
            start = f"1.0 + {match.start()}c"
            end = f"1.0 + {match.end()}c"
            self.text_area.tag_add('string', start, end)

        if 'comments' in rules and rules['comments']:
            for match in re.finditer(rules['comments'], content, re.MULTILINE):
                start = f"1.0 + {match.start()}c"
                end = f"1.0 + {match.end()}c"
                self.text_area.tag_add('comment', start, end)

        self.text_area.config(undo=True)
    
    # --------------------------------------------------------------------------
    # LOGIC: Theme & Config
    # --------------------------------------------------------------------------
    def apply_theme(self):
        theme_name = 'dark' if self.is_dark_theme.get() else 'light'
        colors = self.THEMES[theme_name]
        
        self.root.config(bg=colors['bg'])
        self.text_area.config(
            bg=colors['bg'], 
            fg=colors['fg'], 
            insertbackground=colors['insert']
        )
        self.status_bar.config(
            bg=colors['status_bar_bg'], 
            fg=colors['status_bar_fg']
        )
        self.line_number_bar.config(
            bg=colors['line_num_bg'],
            fg=colors['line_num_fg']
        )
            
        # Re-apply highlighting to ensure colors update if theme changed
        self.highlight_syntax()

    def _get_config_dir(self):
        if sys.platform == "win32":
            app_data = os.environ.get('APPDATA') or os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming')
            config_dir = os.path.join(app_data, "Notepad--")
        else:
            config_dir = os.path.join(os.path.expanduser("~"), ".config", "notepad--")
        os.makedirs(config_dir, exist_ok=True)
        return config_dir

    def _load_config(self):
        if os.path.exists(self.config_file):
            try:
                import json
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.is_dark_theme.set(config.get('is_dark_theme', False))
                    self.show_line_numbers.set(config.get('show_line_numbers', False))
                    self.syntax_highlighting.set(config.get('syntax_highlighting', False))
            except Exception as e:
                print(f"Could not load config: {e}")

    def _save_config(self):
        try:
            import json
            config = {
                'is_dark_theme': self.is_dark_theme.get(),
                'show_line_numbers': self.show_line_numbers.get(),
                'syntax_highlighting': self.syntax_highlighting.get(),
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"Could not save config: {e}")

    # --------------------------------------------------------------------------
    # LOGIC: Menus
    # --------------------------------------------------------------------------
    def create_menus(self):
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", accelerator="Ctrl+N", command=self.new_file)
        file_menu.add_command(label="Open...", accelerator="Ctrl+O", command=self.open_file)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_file)
        file_menu.add_command(label="Save As...", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Print", accelerator="Ctrl+P", command=self.print_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_exit)

        edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=self.text_area.edit_undo)
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=self.text_area.edit_redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", accelerator="Ctrl+X", command=lambda: self.text_area.event_generate('<<Cut>>'))
        edit_menu.add_command(label="Copy", accelerator="Ctrl+C", command=lambda: self.text_area.event_generate('<<Copy>>'))
        edit_menu.add_command(label="Paste", accelerator="Ctrl+V", command=lambda: self.text_area.event_generate('<<Paste>>'))
        edit_menu.add_command(label="Delete", accelerator="Del", command=self.delete_selection)
        edit_menu.add_separator()
        edit_menu.add_command(label="Find...", accelerator="Ctrl+F", command=self.open_find_dialog)
        edit_menu.add_command(label="Replace...", accelerator="Ctrl+H", command=self.open_replace_dialog)
        edit_menu.add_separator()
        edit_menu.add_command(label="Select All", accelerator="Ctrl+A", command=self.select_all)
        edit_menu.add_command(label="Time/Date", accelerator="F5", command=self.insert_time_date)

        format_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Format", menu=format_menu)
        format_menu.add_checkbutton(label="Word Wrap", command=self.toggle_word_wrap)
        format_menu.add_command(label="Font...", command=self.open_font_dialog)

        view_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="View", menu=view_menu)
        view_menu.add_checkbutton(label="Show Line Numbers", variable=self.show_line_numbers, command=self.toggle_line_numbers)
        view_menu.add_checkbutton(label="Dark Theme", variable=self.is_dark_theme, command=self.apply_theme)
        view_menu.add_checkbutton(label="Syntax Highlighting", variable=self.syntax_highlighting, command=self.highlight_syntax)

        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About Notepad--", command=self.show_about)

    def bind_shortcuts(self):
        self.root.bind("<Control-n>", lambda e: self.new_file())
        self.root.bind("<Control-o>", lambda e: self.open_file())
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-p>", lambda e: self.print_file())
        self.root.bind("<Control-f>", lambda e: self.open_find_dialog())
        self.root.bind("<Control-h>", lambda e: self.open_replace_dialog())
        self.root.bind("<F5>", lambda e: self.insert_time_date())

    # --------------------------------------------------------------------------
    # LOGIC: Status & File Operations
    # --------------------------------------------------------------------------
    def on_modified(self, event=None):
        if self.text_area.edit_modified():
            current_title = self.root.title()
            if not current_title.startswith("*"):
                self.root.title("*" + current_title)
            self._on_content_changed()

    def update_status_bar(self, event=None):
        row, col = self.text_area.index(tk.INSERT).split('.')
        col = int(col) + 1
        
        content = self.text_area.get(1.0, tk.END+'-1c') 
        char_count = len(content)
        word_count = len(content.split())
        
        self.status_bar.config(text=f"Ln {row}, Col {col} | Words: {word_count} | Chars: {char_count}")

    def new_file(self):
        if not self.check_save():
            return
        self.text_area.delete(1.0, tk.END)
        self.filename = "Untitled"
        self.file_path = None
        self.current_lang = 'generic' # Reset language
        self.root.title("Notepad--")
        self._on_content_changed()
        self.text_area.edit_modified(False)

    def open_file(self):
        if not self.check_save():
            return
            
        path = filedialog.askopenfilename(defaultextension=".txt", 
                                          filetypes=[("Text Documents", "*.txt"), ("All Files", "*.*")])
        if path:
            self.load_file_content(path)

    def load_file_content(self, path):
        self.file_path = path
        self.filename = os.path.basename(path)
        self.root.title(f"{self.filename} - Notepad--")
        self.text_area.delete(1.0, tk.END)
        
        # Detect syntax based on new file extension
        self.detect_language()
        
        content = ""
        try:
            with open(path, 'rb') as f:
                raw = f.read()
            
            if raw.startswith(codecs.BOM_UTF16_LE):
                content = raw.decode('utf-16-le')
            elif raw.startswith(codecs.BOM_UTF16_BE):
                content = raw.decode('utf-16-be')
            elif raw.startswith(codecs.BOM_UTF8):
                content = raw.decode('utf-8-sig')
            else:
                try:
                    content = raw.decode('utf-8')
                except UnicodeDecodeError:
                    content = raw.decode('latin-1')
                    
            self.text_area.insert(1.0, content)
            self._on_content_changed() # Trigger syntax highlight and line numbers
            self.text_area.edit_modified(False)
        except Exception as e:
            messagebox.showerror("Error", f"Could not read file: {e}")

    def save_file(self):
        if self.file_path is None:
            return self.save_file_as()
        else:
            try:
                content = self.text_area.get(1.0, tk.END+'-1c')
                with open(self.file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.root.title(f"{self.filename} - Notepad--")
                self.text_area.edit_modified(False)
                return True
            except Exception as e:
                messagebox.showerror("Error", str(e))
                return False

    def save_file_as(self):
        path = filedialog.asksaveasfilename(initialfile=self.filename,
                                            defaultextension=".txt",
                                            filetypes=[("Text Documents", "*.txt"), ("All Files", "*.*")])
        if path:
            self.file_path = path
            self.filename = os.path.basename(path)
            self.detect_language() # Re-detect if saving as .py from .txt
            return self.save_file()
        return False

    def check_save(self):
        if self.text_area.edit_modified():
            response = messagebox.askyesnocancel("Notepad--", "Do you want to save changes to " + self.filename + "?")
            if response is True:    
                return self.save_file()
            elif response is False: 
                return True
            else: 
                return False 
        return True

    # --------------------------------------------------------------------------
    # LOGIC: Printing
    # --------------------------------------------------------------------------
    def print_file(self):
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, "npmm_print_job.txt")
        try:
            content = self.text_area.get(1.0, tk.END+'-1c')
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(content)
            print_thread = threading.Thread(target=self._run_print_job, args=(temp_file,), daemon=True)
            print_thread.start()
        except Exception as e:
            messagebox.showerror("Print Error", f"Could not prepare print job: {e}")

    def _run_print_job(self, temp_file):
        try:
            if sys.platform == "win32":
                ps_script_content = f"""
param($filePath)
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
$pd = New-Object System.Windows.Forms.PrintDialog
$pd.UseEXDialog = $true
if ($pd.ShowDialog() -eq 'OK') {{
    $printDoc = New-Object System.Drawing.Printing.PrintDocument
    $printDoc.PrinterSettings = $pd.PrinterSettings
    $printDoc.DocumentName = "Notepad-- Document"
    $printDoc.PrintController = New-Object System.Drawing.Printing.StandardPrintController
    if (Test-Path $filePath) {{ $text = [System.IO.File]::ReadAllText($filePath, [System.Text.Encoding]::UTF8) }} else {{ $text = "Error." }}
    $font = New-Object System.Drawing.Font("Consolas", 12)
    $brush = [System.Drawing.Brushes]::Black
    $format = [System.Drawing.StringFormat]::GenericDefault
    $script:currChar = 0
    $printDoc.add_PrintPage({{
        param($sender, $e)
        $printArea = New-Object System.Drawing.RectangleF($e.MarginBounds.Left, $e.MarginBounds.Top, $e.MarginBounds.Width, $e.MarginBounds.Height)
        $charsFitted = 0; $linesFilled = 0
        $textToPrint = $text.Substring($script:currChar)
        $e.Graphics.MeasureString($textToPrint, $font, $printArea.Size, $format, [ref]$charsFitted, [ref]$linesFilled)
        $e.Graphics.DrawString($textToPrint, $font, $brush, $printArea, $format)
        $script:currChar += $charsFitted
        if ($script:currChar -lt $text.Length) {{ $e.HasMorePages = $true }} else {{ $e.HasMorePages = $false }}
    }})
    try {{ $printDoc.Print() }} catch {{ Write-Error "Printing Failed: $_" }}
}}
"""
                temp_dir = tempfile.gettempdir()
                temp_ps_script = os.path.join(temp_dir, "npmm_print_logic.ps1")
                with open(temp_ps_script, "w", encoding="utf-8") as psf:
                    psf.write(ps_script_content)
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", temp_ps_script, "-filePath", temp_file], startupinfo=startupinfo, check=True)
                if os.path.exists(temp_ps_script):
                    try:
                        os.remove(temp_ps_script) 
                    except:
                        pass
            else:
                subprocess.run(['lp', temp_file], check=True)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Print Error", f"Print process failed: {e}"))
        finally:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

    def on_exit(self):
        if self.check_save():
            self._save_config()
            self.root.destroy()

    # --------------------------------------------------------------------------
    # LOGIC: Editing Utils
    # --------------------------------------------------------------------------
    def delete_selection(self):
        try: 
            self.text_area.delete("sel.first", "sel.last")
            self._on_content_changed()
        except tk.TclError: pass

    def select_all(self):
        self.text_area.tag_add("sel", "1.0", "end")
        return "break"

    def insert_time_date(self):
        now = datetime.now().strftime("%I:%M %p %m/%d/%Y")
        self.text_area.insert(tk.INSERT, now)
        self._on_content_changed()

    # --------------------------------------------------------------------------
    # LOGIC: Find & Replace
    # --------------------------------------------------------------------------
    def open_find_dialog(self):
        if hasattr(self, 'find_window') and self.find_window.winfo_exists():
            self.find_window.lift()
            return
        self.find_window = tk.Toplevel(self.root)
        self._set_window_icon(self.find_window) # Set Icon
        self.find_window.title("Find")
        self.find_window.geometry("340x80")
        self.find_window.resizable(False, False)

        tk.Label(self.find_window, text="Find what:").grid(row=0, column=0, padx=4, pady=4)
        entry_find = tk.Entry(self.find_window, width=25)
        entry_find.grid(row=0, column=1, padx=4, pady=4)
        entry_find.focus_set()

        def find_next():
            target = entry_find.get()
            if target:
                start_pos = self.text_area.index(tk.INSERT)
                pos = self.text_area.search(target, start_pos, stopindex=tk.END)
                if not pos: pos = self.text_area.search(target, "1.0", stopindex=tk.END)
                if pos:
                    end_pos = f"{pos}+{len(target)}c"
                    self.text_area.tag_remove("sel", "1.0", "end")
                    self.text_area.tag_add("sel", pos, end_pos)
                    self.text_area.mark_set(tk.INSERT, end_pos)
                    self.text_area.see(pos)
                else:
                    messagebox.showinfo("Notepad--", f"Cannot find \"{target}\"")

        entry_find.bind('<Return>', lambda e: find_next())
        tk.Button(self.find_window, text="Find Next", command=find_next).grid(row=0, column=2, padx=4, pady=4)

    def open_replace_dialog(self):
        if hasattr(self, 'replace_window') and self.replace_window.winfo_exists():
            self.replace_window.lift()
            return
        self.replace_window = tk.Toplevel(self.root)
        self._set_window_icon(self.replace_window) # Set Icon
        self.replace_window.title("Replace")
        self.replace_window.geometry("380x120")
        self.replace_window.resizable(False, False)

        tk.Label(self.replace_window, text="Find what:").grid(row=0, column=0, sticky="e")
        entry_find = tk.Entry(self.replace_window, width=20)
        entry_find.grid(row=0, column=1, padx=2, pady=2)
        tk.Label(self.replace_window, text="Replace with:").grid(row=1, column=0, sticky="e")
        entry_replace = tk.Entry(self.replace_window, width=20)
        entry_replace.grid(row=1, column=1, padx=2, pady=2)
        
        def replace_one():
            target = entry_find.get()
            replacement = entry_replace.get()
            try:
                sel_start = self.text_area.index("sel.first")
                sel_end = self.text_area.index("sel.last")
                if self.text_area.get(sel_start, sel_end) == target:
                    self.text_area.delete(sel_start, sel_end)
                    self.text_area.insert(sel_start, replacement)
                    self._on_content_changed()
            except tk.TclError: pass
            start_pos = self.text_area.index(tk.INSERT)
            pos = self.text_area.search(target, start_pos, stopindex=tk.END)
            if pos:
                end_pos = f"{pos}+{len(target)}c"
                self.text_area.tag_remove("sel", "1.0", "end")
                self.text_area.tag_add("sel", pos, end_pos)
                self.text_area.mark_set(tk.INSERT, end_pos)
                self.text_area.see(pos)

        def replace_all():
            target = entry_find.get()
            replacement = entry_replace.get()
            if not target: return
            count = 0
            current_pos = "1.0"
            while True:
                pos = self.text_area.search(target, current_pos, stopindex=tk.END)
                if not pos: break
                end_pos = f"{pos}+{len(target)}c"
                self.text_area.delete(pos, end_pos)
                self.text_area.insert(pos, replacement)
                current_pos = f"{pos}+{len(replacement)}c"
                count += 1
            if count > 0: self._on_content_changed()
            messagebox.showinfo("Notepad--", f"Replaced {count} occurrences.")

        tk.Button(self.replace_window, text="Find Next", command=replace_one).grid(row=0, column=2, padx=4, pady=2)
        tk.Button(self.replace_window, text="Replace", command=replace_one).grid(row=1, column=2, padx=4, pady=2)
        tk.Button(self.replace_window, text="Replace All", command=replace_all).grid(row=2, column=2, padx=4, pady=2)

    def toggle_word_wrap(self):
        self.word_wrap = not self.word_wrap
        self.text_area.config(wrap=tk.WORD if self.word_wrap else tk.NONE)

    def apply_font(self):
        new_font = font.Font(family=self.current_font_family, size=self.current_font_size)
        self.text_area.configure(font=new_font)
        self.line_number_bar.configure(font=new_font) # Sync font

    def open_font_dialog(self):
        font_window = tk.Toplevel(self.root)
        self._set_window_icon(font_window) # Set Icon
        font_window.title("Font")
        font_window.geometry("400x300")
        
        frame_family = tk.Frame(font_window)
        frame_family.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        frame_size = tk.Frame(font_window)
        frame_size.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        tk.Label(frame_family, text="Font:").pack(anchor="w")
        tk.Label(frame_size, text="Size:").pack(anchor="w")

        families = list(font.families())
        families.sort()
        list_family = tk.Listbox(frame_family, exportselection=False)
        list_family.pack(fill=tk.BOTH, expand=True)
        scrollbar_fam = tk.Scrollbar(list_family)
        scrollbar_fam.pack(side=tk.RIGHT, fill=tk.Y)
        list_family.config(yscrollcommand=scrollbar_fam.set)
        scrollbar_fam.config(command=list_family.yview)
        for f in families: list_family.insert(tk.END, f)
        
        try:
            idx = families.index(self.current_font_family)
            list_family.selection_set(idx)
            list_family.see(idx)
        except: pass

        sizes = [8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 36, 48, 72]
        list_size = tk.Listbox(frame_size, width=10, exportselection=False)
        list_size.pack(fill=tk.BOTH, expand=True)
        for s in sizes: list_size.insert(tk.END, str(s))

        try:
            if self.current_font_size in sizes:
                idx = sizes.index(self.current_font_size)
                list_size.selection_set(idx)
                list_size.see(idx)
        except: pass

        def on_ok():
            fam_idx = list_family.curselection()
            if fam_idx: self.current_font_family = list_family.get(fam_idx[0])
            size_idx = list_size.curselection()
            if size_idx: self.current_font_size = int(list_size.get(size_idx[0]))
            self.apply_font()
            font_window.destroy()

        btn_frame = tk.Frame(font_window)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        tk.Button(btn_frame, text="Cancel", command=font_window.destroy, width=10).pack(side=tk.RIGHT, padx=10)
        tk.Button(btn_frame, text="OK", command=on_ok, width=10).pack(side=tk.RIGHT, padx=10)

    # --------------------------------------------------------------------------
    # LOGIC: About & Links
    # --------------------------------------------------------------------------
    def show_about(self):
        about_win = tk.Toplevel(self.root)
        self._set_window_icon(about_win) # Set Icon
        about_win.title("About Notepad--")
        about_win.geometry("300x150")
        about_win.resizable(False, False)
        
        tk.Label(about_win, text="Notepad-- v2.0", font=("Arial", 12, "bold")).pack(pady=(15, 5))
        tk.Label(about_win, text="A recreation of the classic Notepad in Python.").pack()
        
        link_font = font.Font(about_win, family="Arial", size=10, underline=True)
        lbl_link = tk.Label(about_win, text="View on GitHub", fg="blue", cursor="hand2", font=link_font)
        lbl_link.pack(pady=5)
        lbl_link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/MZGSZM/Notepad--"))
        
        tk.Button(about_win, text="Close", command=about_win.destroy).pack(pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = NotepadMinusMinus(root)
    root.mainloop()