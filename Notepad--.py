import tkinter as tk
from tkinter import filedialog, messagebox, font
import os
import sys
import codecs
import subprocess
import threading
from datetime import datetime

class NotepadMinusMinus:
    def __init__(self, root):
        self.root = root
        self.root.title("Notepad--")
        self.root.geometry("800x600")
        
        # --- State Variables ---
        self.filename = "Untitled"
        self.file_path = None
        self.word_wrap = False
        
        # Default Font State
        self.current_font_family = "Consolas"
        self.current_font_size = 11
        
        # --- UI Layout Setup ---
        # 1. Status Bar (Packed first at BOTTOM to stick to the very bottom)
        self.status_bar = tk.Label(self.root, text="Ln 1, Col 1  |  Words: 0  |  Chars: 0", 
                                   bd=1, relief=tk.SUNKEN, anchor=tk.E, padx=10)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # 2. Main Frame (Occupies the rest of the space)
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        # 3. Scrollbars and Text Area
        self.scrollbar_y = tk.Scrollbar(self.main_frame)
        self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.scrollbar_x = tk.Scrollbar(self.main_frame, orient=tk.HORIZONTAL)
        self.scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

        # inactiveselectbackground ensures highlight stays visible 
        # when focus moves to the Find/Replace dialogs.
        self.text_area = tk.Text(self.main_frame, undo=True, wrap=tk.NONE,
                                 selectbackground="#0078D7", 
                                 selectforeground="white",
                                 inactiveselectbackground="#0078D7",
                                 yscrollcommand=self.scrollbar_y.set,
                                 xscrollcommand=self.scrollbar_x.set)
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        
        self.scrollbar_y.config(command=self.text_area.yview)
        self.scrollbar_x.config(command=self.text_area.xview)
        
        self.apply_font()

        # --- Event Binding for Status & Modified Checks ---
        # Update status bar on key release and mouse clicks
        self.text_area.bind("<KeyRelease>", self.update_status_bar)
        self.text_area.bind("<ButtonRelease>", self.update_status_bar)
        self.text_area.bind("<<Modified>>", self.on_modified)

        # --- Menus ---
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)
        self.create_menus()
        self.bind_shortcuts()
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

        # Initialize Modified State
        self.text_area.edit_modified(False)

    def create_menus(self):
        # File
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

        # Edit
        edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=self.text_area.edit_undo)
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=self.text_area.edit_redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", accelerator="Ctrl+X", command=lambda: self.root.focus_get().event_generate('<<Cut>>'))
        edit_menu.add_command(label="Copy", accelerator="Ctrl+C", command=lambda: self.root.focus_get().event_generate('<<Copy>>'))
        edit_menu.add_command(label="Paste", accelerator="Ctrl+V", command=lambda: self.root.focus_get().event_generate('<<Paste>>'))
        edit_menu.add_command(label="Delete", accelerator="Del", command=self.delete_selection)
        edit_menu.add_separator()
        edit_menu.add_command(label="Find...", accelerator="Ctrl+F", command=self.open_find_dialog)
        edit_menu.add_command(label="Replace...", accelerator="Ctrl+H", command=self.open_replace_dialog)
        edit_menu.add_separator()
        edit_menu.add_command(label="Select All", accelerator="Ctrl+A", command=self.select_all)
        edit_menu.add_command(label="Time/Date", accelerator="F5", command=self.insert_time_date)

        # Format
        format_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Format", menu=format_menu)
        format_menu.add_checkbutton(label="Word Wrap", command=self.toggle_word_wrap)
        format_menu.add_command(label="Font...", command=self.open_font_dialog)

        # Help
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

    # --- Status Bar & Events ---

    def on_modified(self, event=None):
        if self.text_area.edit_modified():
            # Update Title with *
            current_title = self.root.title()
            if not current_title.startswith("*"):
                self.root.title("*" + current_title)
            
            # Simple approach: Update status bar on every keystroke (already bound), 
            # use edit_modified only for the save prompt state.
            self.update_status_bar()

    def update_status_bar(self, event=None):
        # Position
        row, col = self.text_area.index(tk.INSERT).split('.')
        col = int(col) + 1
        
        # Content stats
        content = self.text_area.get(1.0, tk.END+'-1c') # -1c to remove the always-present newline at end
        char_count = len(content)
        word_count = len(content.split())
        
        self.status_bar.config(text=f"Ln {row}, Col {col}  |  Words: {word_count}  |  Chars: {char_count}")

    # --- File Operations ---

    def new_file(self):
        if not self.check_save():
            return
        self.text_area.delete(1.0, tk.END)
        self.filename = "Untitled"
        self.file_path = None
        self.root.title("Notepad--")
        self.update_status_bar()
        self.text_area.edit_modified(False)

    def open_file(self):
        if not self.check_save():
            return
            
        path = filedialog.askopenfilename(defaultextension=".txt", 
                                          filetypes=[("Text Documents", "*.txt"), ("All Files", "*.*")])
        if not path: return
        
        self.file_path = path
        self.filename = os.path.basename(path)
        self.root.title(f"{self.filename} - Notepad--")
        self.text_area.delete(1.0, tk.END)
        
        # BOM Detection
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
            self.update_status_bar()
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
            return self.save_file()
        return False

    def check_save(self):
        """Returns True if it's safe to proceed (saved, discarded, or not modified)."""
        if self.text_area.edit_modified():
            response = messagebox.askyesnocancel("Notepad--", "Do you want to save changes to " + self.filename + "?")
            if response is True:   # Save
                return self.save_file()
            elif response is False: # Don't save
                return True
            else: # Cancel
                return False
        return True

    def print_file(self):
        # Temp file for content
        temp_file = os.path.abspath("temp_print_job.txt")
        try:
            content = self.text_area.get(1.0, tk.END+'-1c')
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(content)
            
            # Start printing in a separate thread to avoid freezing GUI
            print_thread = threading.Thread(target=self._run_print_job, args=(temp_file,), daemon=True)
            print_thread.start()
            
        except Exception as e:
            messagebox.showerror("Print Error", f"Could not prepare print job: {e}")

    def _run_print_job(self, temp_file):
        try:
            if sys.platform == "win32":
                # --- Windows Native .NET Printing Strategy ---
                ps_script_content = f"""
param($filePath)
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

# 1. Show Print Dialog
$pd = New-Object System.Windows.Forms.PrintDialog
$pd.UseEXDialog = $true

if ($pd.ShowDialog() -eq 'OK') {{
    # 2. Setup Print Document
    $printDoc = New-Object System.Drawing.Printing.PrintDocument
    $printDoc.PrinterSettings = $pd.PrinterSettings
    $printDoc.DocumentName = "Notepad-- Document"
    
    # SUPPRESS the 'Printing...' status dialog to prevent freezing/hanging
    $printDoc.PrintController = New-Object System.Drawing.Printing.StandardPrintController
    
    # 3. Read Content
    if (Test-Path $filePath) {{
        $lines = Get-Content $filePath
    }} else {{
        $lines = @("Error: Could not read content.")
    }}
    
    # Setup Font (Consolas 11 to match editor)
    $font = New-Object System.Drawing.Font("Consolas", 11)
    $brush = [System.Drawing.Brushes]::Black
    
    # Track current line index across pages (script scope)
    $script:lineIdx = 0
    
    # 4. Define Print Page Event
    $printDoc.add_PrintPage({{
        param($sender, $e)
        
        $y = $e.MarginBounds.Top
        $left = $e.MarginBounds.Left
        $lineHeight = $font.GetHeight($e.Graphics)
        
        # Print lines until page is full
        while ($y + $lineHeight -lt $e.MarginBounds.Bottom -and $script:lineIdx -lt $lines.Count) {{
            $line = $lines[$script:lineIdx]
            
            # DrawString handles the text rendering
            $e.Graphics.DrawString($line, $font, $brush, $left, $y)
            
            $y += $lineHeight
            $script:lineIdx++
        }}
        
        # Check if more pages are needed
        if ($script:lineIdx -lt $lines.Count) {{
            $e.HasMorePages = $true
        }} else {{
            $e.HasMorePages = $false
        }}
    }})
    
    # 5. Print
    try {{
        $printDoc.Print()
    }} catch {{
        Write-Error "Printing Failed: $_"
    }}
}}
"""
                temp_ps_script = os.path.abspath("temp_print_logic.ps1")
                with open(temp_ps_script, "w", encoding="utf-8") as psf:
                    psf.write(ps_script_content)
                
                # Execute PowerShell script (Hidden window)
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                subprocess.run(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-File", temp_ps_script, "-filePath", temp_file],
                    startupinfo=startupinfo,
                    check=True
                )
                
                # Cleanup PS script
                if os.path.exists(temp_ps_script):
                    try: os.remove(temp_ps_script)
                    except: pass
                
            else:
                # Unix/Linux/Mac (CUPS)
                subprocess.run(['lp', temp_file], check=True)
                
        except subprocess.CalledProcessError as e:
            self.root.after(0, lambda: messagebox.showerror("Print Error", f"The print process failed.\n{e}"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Print Error", f"Could not print: {e}"))
        finally:
            # Clean up content file
            if os.path.exists(temp_file):
                try: os.remove(temp_file)
                except: pass

    def on_exit(self):
        if self.check_save():
            self.root.destroy()

    # --- Editing ---
    def delete_selection(self):
        try: 
            self.text_area.delete("sel.first", "sel.last")
            self.update_status_bar()
        except tk.TclError: pass

    def select_all(self):
        self.text_area.tag_add("sel", "1.0", "end")
        return "break"

    def insert_time_date(self):
        now = datetime.now().strftime("%I:%M %p %m/%d/%Y")
        self.text_area.insert(tk.INSERT, now)
        self.update_status_bar()

    # --- Find & Replace ---

    def open_find_dialog(self):
        if hasattr(self, 'find_window') and self.find_window.winfo_exists():
            self.find_window.lift()
            return
            
        self.find_window = tk.Toplevel(self.root)
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
                if not pos: 
                    pos = self.text_area.search(target, "1.0", stopindex=tk.END)

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
                    self.update_status_bar()
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
            if count > 0: self.update_status_bar()
            messagebox.showinfo("Notepad--", f"Replaced {count} occurrences.")

        tk.Button(self.replace_window, text="Find Next", command=replace_one).grid(row=0, column=2, padx=4, pady=2)
        tk.Button(self.replace_window, text="Replace", command=replace_one).grid(row=1, column=2, padx=4, pady=2)
        tk.Button(self.replace_window, text="Replace All", command=replace_all).grid(row=2, column=2, padx=4, pady=2)

    # --- Format ---

    def toggle_word_wrap(self):
        self.word_wrap = not self.word_wrap
        self.text_area.config(wrap=tk.WORD if self.word_wrap else tk.NONE)

    def apply_font(self):
        new_font = font.Font(family=self.current_font_family, size=self.current_font_size)
        self.text_area.configure(font=new_font)

    def open_font_dialog(self):
        # A dual-listbox dialog for Family and Size
        font_window = tk.Toplevel(self.root)
        font_window.title("Font")
        font_window.geometry("400x300")
        
        # Frames
        frame_family = tk.Frame(font_window)
        frame_family.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        frame_size = tk.Frame(font_window)
        frame_size.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)

        # Labels
        tk.Label(frame_family, text="Font:").pack(anchor="w")
        tk.Label(frame_size, text="Size:").pack(anchor="w")

        # Family List
        families = list(font.families())
        families.sort()
        list_family = tk.Listbox(frame_family, exportselection=False)
        list_family.pack(fill=tk.BOTH, expand=True)
        scrollbar_fam = tk.Scrollbar(list_family)
        scrollbar_fam.pack(side=tk.RIGHT, fill=tk.Y)
        list_family.config(yscrollcommand=scrollbar_fam.set)
        scrollbar_fam.config(command=list_family.yview)

        for f in families:
            list_family.insert(tk.END, f)
        
        # Select current
        try:
            idx = families.index(self.current_font_family)
            list_family.selection_set(idx)
            list_family.see(idx)
        except: pass

        # Size List
        sizes = [8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 36, 48, 72]
        list_size = tk.Listbox(frame_size, width=10, exportselection=False)
        list_size.pack(fill=tk.BOTH, expand=True)
        
        for s in sizes:
            list_size.insert(tk.END, str(s))

        # Select current size
        try:
            if self.current_font_size in sizes:
                idx = sizes.index(self.current_font_size)
                list_size.selection_set(idx)
                list_size.see(idx)
        except: pass

        def on_ok():
            # Get Family
            fam_idx = list_family.curselection()
            if fam_idx:
                self.current_font_family = list_family.get(fam_idx[0])
            
            # Get Size
            size_idx = list_size.curselection()
            if size_idx:
                self.current_font_size = int(list_size.get(size_idx[0]))
            
            self.apply_font()
            font_window.destroy()

        # Button Frame (Bottom)
        btn_frame = tk.Frame(font_window)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        
        tk.Button(btn_frame, text="Cancel", command=font_window.destroy, width=10).pack(side=tk.RIGHT, padx=10)
        tk.Button(btn_frame, text="OK", command=on_ok, width=10).pack(side=tk.RIGHT, padx=10)

    # --- Help ---
    def show_about(self):
        messagebox.showinfo("About Notepad--", "Notepad-- v1.3.2\n\nUpdates:\n- Fixed PDF printing freeze (Threading)\n- Suppressed default print popup")

if __name__ == "__main__":
    root = tk.Tk()
    app = NotepadMinusMinus(root)
    root.mainloop()