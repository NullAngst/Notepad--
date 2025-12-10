import tkinter as tk
from tkinter import filedialog, messagebox, font
import os
import sys
import codecs
import subprocess
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
        
        # --- UI Setup ---
        # inactiveselectbackground ensures highlight stays visible 
        # when focus moves to the Find/Replace dialogs.
        self.text_area = tk.Text(self.root, undo=True, wrap=tk.NONE,
                                 selectbackground="#0078D7", 
                                 selectforeground="white",
                                 inactiveselectbackground="#0078D7") 
        self.text_area.pack(fill=tk.BOTH, expand=1)
        
        self.scrollbar_y = tk.Scrollbar(self.text_area)
        self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.scrollbar_x = tk.Scrollbar(self.text_area, orient=tk.HORIZONTAL)
        self.scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.text_area.config(yscrollcommand=self.scrollbar_y.set, xscrollcommand=self.scrollbar_x.set)
        self.scrollbar_y.config(command=self.text_area.yview)
        self.scrollbar_x.config(command=self.text_area.xview)

        self.apply_font()

        # --- Menus ---
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)
        self.create_menus()
        self.bind_shortcuts()
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

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

    # --- File Operations ---

    def new_file(self):
        self.text_area.delete(1.0, tk.END)
        self.filename = "Untitled"
        self.file_path = None
        self.root.title("Notepad--")

    def open_file(self):
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
        except Exception as e:
            messagebox.showerror("Error", f"Could not read file: {e}")

    def save_file(self):
        if self.file_path is None:
            self.save_file_as()
        else:
            try:
                content = self.text_area.get(1.0, tk.END).rstrip()
                with open(self.file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.root.title(f"{self.filename} - Notepad--")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def save_file_as(self):
        path = filedialog.asksaveasfilename(initialfile="Untitled.txt",
                                            defaultextension=".txt",
                                            filetypes=[("Text Documents", "*.txt"), ("All Files", "*.*")])
        if path:
            self.file_path = path
            self.filename = os.path.basename(path)
            self.save_file()

    def print_file(self):
        # Use 'notepad.exe /p' for reliable Windows printing
        temp_file = os.path.abspath("temp_print.txt")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(self.text_area.get(1.0, tk.END))
                
            if sys.platform == "win32":
                # This opens the hidden notepad instance, prints to default printer, and closes.
                subprocess.run(['notepad.exe', '/p', temp_file], check=True)
            else:
                # Unix/Linux/Mac
                subprocess.run(['lp', temp_file], check=True)
        except Exception as e:
            messagebox.showerror("Print Error", f"Could not print: {e}")
        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                try: os.remove(temp_file)
                except: pass

    def on_exit(self):
        self.root.destroy()

    # --- Editing ---
    def delete_selection(self):
        try: self.text_area.delete("sel.first", "sel.last")
        except tk.TclError: pass

    def select_all(self):
        self.text_area.tag_add("sel", "1.0", "end")
        return "break"

    def insert_time_date(self):
        now = datetime.now().strftime("%I:%M %p %m/%d/%Y")
        self.text_area.insert(tk.INSERT, now)

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

        tk.Button(font_window, text="OK", command=on_ok, width=10).pack(side=tk.BOTTOM, pady=5)
        tk.Button(font_window, text="Cancel", command=font_window.destroy, width=10).pack(side=tk.BOTTOM, pady=5)

    # --- Help ---
    def show_about(self):
        messagebox.showinfo("About Notepad--", "Notepad-- v1.0\nA lightweight text editor.\n\nWritten in Python/Tkinter.")

if __name__ == "__main__":
    root = tk.Tk()
    app = NotepadMinusMinus(root)
    root.mainloop()