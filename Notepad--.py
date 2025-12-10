import tkinter as tk
from tkinter import filedialog, messagebox, font
import os
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
        self.current_font_family = "Consolas"
        self.current_font_size = 11
        
        # --- UI Setup ---
        # The main text area. Undo=True enables Ctrl+Z/Ctrl+Y natively
        self.text_area = tk.Text(self.root, undo=True, wrap=tk.NONE)
        self.text_area.pack(fill=tk.BOTH, expand=1)
        
        # Scrollbars (Classic Notepad has them)
        self.scrollbar_y = tk.Scrollbar(self.text_area)
        self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_area.config(yscrollcommand=self.scrollbar_y.set)
        self.scrollbar_y.config(command=self.text_area.yview)

        # Set Default Font
        self.update_font()

        # --- Menus ---
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)
        self.create_menus()
        
        # --- Key Bindings ---
        self.bind_shortcuts()
        
        # Handle "X" button
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

    def create_menus(self):
        # File Menu
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", accelerator="Ctrl+N", command=self.new_file)
        file_menu.add_command(label="Open...", accelerator="Ctrl+O", command=self.open_file)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_file)
        file_menu.add_command(label="Save As...", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_exit)

        # Edit Menu
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

        # Format Menu
        format_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Format", menu=format_menu)
        format_menu.add_checkbutton(label="Word Wrap", command=self.toggle_word_wrap)
        format_menu.add_command(label="Font...", command=self.change_font)

        # Help Menu
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About Notepad--", command=self.show_about)

    def bind_shortcuts(self):
        self.root.bind("<Control-n>", lambda e: self.new_file())
        self.root.bind("<Control-o>", lambda e: self.open_file())
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-f>", lambda e: self.open_find_dialog())
        self.root.bind("<Control-h>", lambda e: self.open_replace_dialog())
        self.root.bind("<F5>", lambda e: self.insert_time_date())

    # --- Logic ---

    def new_file(self):
        self.text_area.delete(1.0, tk.END)
        self.filename = "Untitled"
        self.file_path = None
        self.root.title("Notepad--")

    def open_file(self):
        path = filedialog.askopenfilename(defaultextension=".txt", 
                                          filetypes=[("Text Documents", "*.txt"), ("All Files", "*.*")])
        if path:
            self.file_path = path
            self.filename = os.path.basename(path)
            self.root.title(f"{self.filename} - Notepad--")
            self.text_area.delete(1.0, tk.END)
            try:
                # Python handles standard text encodings automatically
                with open(path, "r", encoding="utf-8") as f:
                    self.text_area.insert(1.0, f.read())
            except UnicodeDecodeError:
                # Fallback for ANSI/Legacy files
                with open(path, "r", encoding="latin-1") as f:
                    self.text_area.insert(1.0, f.read())

    def save_file(self):
        if self.file_path is None:
            self.save_file_as()
        else:
            try:
                content = self.text_area.get(1.0, tk.END)
                # We strip the very last newline that Tkinter adds automatically
                with open(self.file_path, "w", encoding="utf-8") as f:
                    f.write(content.rstrip())
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

    def on_exit(self):
        # In a full app, you'd check for unsaved changes here
        self.root.destroy()

    # --- Edit Functions ---

    def delete_selection(self):
        try:
            self.text_area.delete("sel.first", "sel.last")
        except tk.TclError:
            pass # No selection

    def select_all(self):
        self.text_area.tag_add("sel", "1.0", "end")
        return "break" # prevent default behavior

    def insert_time_date(self):
        now = datetime.now()
        # Format: 10:23 PM 12/09/2025 (Mimicking the C++ code)
        dt_string = now.strftime("%I:%M %p %m/%d/%Y")
        self.text_area.insert(tk.INSERT, dt_string)

    # --- Find & Replace (Mimicking Win32 Dialogs) ---

    def open_find_dialog(self):
        self.find_window = tk.Toplevel(self.root)
        self.find_window.title("Find")
        self.find_window.geometry("300x80")
        self.find_window.resizable(False, False)

        tk.Label(self.find_window, text="Find what:").grid(row=0, column=0, padx=4, pady=4)
        entry_find = tk.Entry(self.find_window, width=25)
        entry_find.grid(row=0, column=1, padx=4, pady=4)
        entry_find.focus_set()

        def find_next():
            target = entry_find.get()
            if target:
                start_pos = self.text_area.index(tk.INSERT)
                # Search returns "line.col" or empty string
                pos = self.text_area.search(target, start_pos, stopindex=tk.END)
                
                # If not found from cursor, wrap to top (Standard notepad behavior usually asks, but we simplify)
                if not pos: 
                    pos = self.text_area.search(target, "1.0", stopindex=tk.END)

                if pos:
                    # Calculate end position for selection
                    end_pos = f"{pos}+{len(target)}c"
                    self.text_area.tag_remove("sel", "1.0", "end")
                    self.text_area.tag_add("sel", pos, end_pos)
                    self.text_area.mark_set(tk.INSERT, end_pos)
                    self.text_area.see(pos)
                else:
                    messagebox.showinfo("Notepad--", f"Cannot find \"{target}\"")

        tk.Button(self.find_window, text="Find Next", command=find_next).grid(row=0, column=2, padx=4, pady=4)

    def open_replace_dialog(self):
        self.replace_window = tk.Toplevel(self.root)
        self.replace_window.title("Replace")
        self.replace_window.geometry("350x120")
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
            
            # Check if current selection matches target
            try:
                sel_start = self.text_area.index("sel.first")
                sel_end = self.text_area.index("sel.last")
                current_sel = self.text_area.get(sel_start, sel_end)
                if current_sel == target:
                    self.text_area.delete(sel_start, sel_end)
                    self.text_area.insert(sel_start, replacement)
            except tk.TclError:
                pass
            
            # Find next
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
            
            # Simple Replace All logic
            count = 0
            # Start from top
            current_pos = "1.0"
            while True:
                pos = self.text_area.search(target, current_pos, stopindex=tk.END)
                if not pos: break
                
                end_pos = f"{pos}+{len(target)}c"
                self.text_area.delete(pos, end_pos)
                self.text_area.insert(pos, replacement)
                
                # Move pointer past the replacement
                current_pos = f"{pos}+{len(replacement)}c"
                count += 1
            
            messagebox.showinfo("Notepad--", f"Replaced {count} occurrences.")

        tk.Button(self.replace_window, text="Find Next", command=replace_one).grid(row=0, column=2, padx=4, pady=2)
        tk.Button(self.replace_window, text="Replace", command=replace_one).grid(row=1, column=2, padx=4, pady=2)
        tk.Button(self.replace_window, text="Replace All", command=replace_all).grid(row=2, column=2, padx=4, pady=2)

    # --- Format Functions ---

    def toggle_word_wrap(self):
        self.word_wrap = not self.word_wrap
        # Tkinter makes this easy: just change the wrap mode
        self.text_area.config(wrap=tk.WORD if self.word_wrap else tk.NONE)

    def update_font(self):
        new_font = font.Font(family=self.current_font_family, size=self.current_font_size)
        self.text_area.configure(font=new_font)

    def change_font(self):
        # Tkinter doesn't have a native "Font Chooser" dialog like Win32.
        # We'll use a simple input for now to keep dependencies low.
        res = messagebox.askyesno("Font", "Toggle Font Size?\n\nYes = Bigger (14)\nNo = Default (11)")
        self.current_font_size = 14 if res else 11
        self.update_font()

    def show_about(self):
        messagebox.showinfo("About", "Notepad-- Python Edition\nClassic Recreation.\nRunning on Tkinter.")

if __name__ == "__main__":
    root = tk.Tk()
    # Add an icon if you have one, otherwise skip
    # root.iconbitmap("icon.ico") 
    app = NotepadMinusMinus(root)
    root.mainloop()