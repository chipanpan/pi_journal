"""Keyboard-first Tkinter interface for the daily journal."""

import re
import tkinter as tk
from datetime import date, timedelta
from pathlib import Path
from tkinter import filedialog, font as tkfont, messagebox, ttk

import calendar as journal_calendar
import categories
import db
import editor as text_editor
import settings


THEMES = {
    "light": {
        "bg": "#f4f1ea", "panel": "#e7e2d8", "text": "#25231f",
        "muted": "#6c685f", "accent": "#365f74", "select": "#adc8d6",
        "highlight": "#ffe58a", "command": "#8b4b35",
    },
    "dark": {
        "bg": "#202326", "panel": "#292d31", "text": "#e9e4da",
        "muted": "#9aa0a6", "accent": "#83b6c9", "select": "#425e69",
        "highlight": "#66591f", "command": "#e5a37c",
    },
    "sepia": {
        "bg": "#f1e5c8", "panel": "#dfcfaa", "text": "#493a28",
        "muted": "#7a674e", "accent": "#7e5533", "select": "#cbb787",
        "highlight": "#e9c85d", "command": "#965b36",
    },
}

INLINE_PATTERNS = (
    ("bold", re.compile(r"\*\*(\S(?:[^\n]*?\S)?)\*\*"), 2),
    ("highlight", re.compile(r"==(\S(?:[^\n]*?\S)?)=="), 2),
    ("italic", re.compile(r"(?<!\*)\*(\S(?:[^\n]*?\S)?)\*(?!\*)"), 1),
)


class JournalApp:
    AUTOSAVE_MS = 900

    def __init__(self, root, connection):
        self.root = root
        self.connection = connection
        self.preferences = settings.load()
        self.day = date.today()
        self.calendar_day = self.day
        self.dirty = False
        self.save_job = None
        self.sidebar_open = bool(self.preferences["sidebar_open"])
        self.illustration_image = None
        self._build_window()
        self._build_styles()
        self._build_ui()
        if not self.sidebar_open:
            self.sidebar.pack_forget()
        self._bind_keys()
        self.apply_theme(self.preferences["theme"])
        self.set_fullscreen(bool(self.preferences["fullscreen"]))
        self.load_illustration(self.preferences["illustration"], quiet=True)
        self.open_day(self.day, save_first=False)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _build_window(self):
        self.root.title("Daily Journal")
        self.root.minsize(480, 300)
        self.root.geometry("800x480")

    def _build_styles(self):
        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        families = set(tkfont.families(self.root))
        body_family = next((name for name in ("DejaVu Sans", "Noto Sans", "Arial") if name in families), "TkDefaultFont")
        self.body_font = tkfont.Font(family=body_family, size=13)
        self.bold_font = tkfont.Font(family=body_family, size=13, weight="bold")
        self.italic_font = tkfont.Font(family=body_family, size=13, slant="italic")
        self.title_font = tkfont.Font(family=body_family, size=17, weight="bold")
        self.small_font = tkfont.Font(family=body_family, size=9)

    def _build_ui(self):
        self.container = ttk.Frame(self.root)
        self.container.pack(fill="both", expand=True)

        self.sidebar = ttk.Frame(self.container, width=200, padding=(8, 7))
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        month_bar = ttk.Frame(self.sidebar)
        month_bar.pack(fill="x")
        ttk.Button(month_bar, text="‹", width=3, command=lambda: self.change_calendar_month(-1)).pack(side="left")
        self.month_label = ttk.Label(month_bar, anchor="center", font=self.bold_font)
        self.month_label.pack(side="left", fill="x", expand=True)
        ttk.Button(month_bar, text="›", width=3, command=lambda: self.change_calendar_month(1)).pack(side="right")

        self.weekdays = ttk.Frame(self.sidebar)
        self.weekdays.pack(fill="x", pady=(7, 1))
        for column, label in enumerate(("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")):
            self.weekdays.columnconfigure(column, weight=1)
            ttk.Label(self.weekdays, text=label, anchor="center", font=self.small_font).grid(row=0, column=column, sticky="ew")

        self.calendar_frame = ttk.Frame(self.sidebar)
        self.calendar_frame.pack(fill="x")
        for column in range(7):
            self.calendar_frame.columnconfigure(column, weight=1)
        self.calendar_buttons = []
        for row in range(6):
            row_buttons = []
            for column in range(7):
                button = tk.Button(
                    self.calendar_frame, width=3, relief="flat", borderwidth=0,
                    highlightthickness=0, padx=0, pady=0,
                    font=self.small_font, takefocus=False,
                )
                button.grid(row=row, column=column, sticky="nsew")
                row_buttons.append(button)
            self.calendar_buttons.append(row_buttons)

        ttk.Separator(self.sidebar).pack(fill="x", pady=6)
        ttk.Button(self.sidebar, text="Today", command=lambda: self.open_day(date.today())).pack(fill="x", pady=2)
        illustration_bar = ttk.Frame(self.sidebar)
        illustration_bar.pack(fill="x", pady=2)
        ttk.Button(illustration_bar, text="Illustration…", command=self.choose_illustration).pack(side="left", fill="x", expand=True)
        ttk.Button(illustration_bar, text="×", width=3, command=self.remove_illustration).pack(side="right", padx=(3, 0))
        self.sidebar_hint = ttk.Label(
            self.sidebar, text="F9 sidebar · F11 fullscreen\nCtrl+←/→ change day",
            justify="left", font=self.small_font,
        )
        self.sidebar_hint.pack(side="bottom", anchor="w")

        self.main = ttk.Frame(self.container, padding=(14, 10, 14, 8))
        self.main.pack(side="left", fill="both", expand=True)

        header = ttk.Frame(self.main)
        header.pack(fill="x", pady=(0, 8))
        ttk.Button(header, text="☰", width=3, command=self.toggle_sidebar).pack(side="left", padx=(0, 8))
        self.date_label = ttk.Label(header, font=self.title_font)
        self.date_label.pack(side="left", fill="x", expand=True)
        self.status_label = ttk.Label(header, text="", font=self.small_font)
        self.status_label.pack(side="right", padx=8)
        self.theme_box = ttk.Combobox(header, values=tuple(THEMES), width=7, state="readonly", takefocus=False)
        self.theme_box.set(self.preferences["theme"] if self.preferences["theme"] in THEMES else "dark")
        self.theme_box.bind("<<ComboboxSelected>>", lambda _event: self.apply_theme(self.theme_box.get()))
        self.theme_box.pack(side="right")

        toolbar = ttk.Frame(self.main)
        toolbar.pack(fill="x", pady=(0, 6))
        for label, command in (
            ("B", lambda: self.format_selection("bold")),
            ("I", lambda: self.format_selection("italic")),
            ("Highlight", lambda: self.format_selection("highlight")),
            ("• List", self.toggle_bullets),
        ):
            ttk.Button(toolbar, text=label, command=command, takefocus=False).pack(side="left", padx=(0, 4))

        self.editor_frame = ttk.Frame(self.main)
        self.editor_frame.pack(fill="both", expand=True)
        self.editor = tk.Text(
            self.editor_frame, wrap="word", undo=True, autoseparators=True,
            maxundo=100, borderwidth=0, padx=10, pady=10,
            font=self.body_font, insertwidth=2,
        )
        scrollbar = ttk.Scrollbar(self.editor_frame, orient="vertical", command=self.editor.yview)
        self.editor.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.editor.pack(side="left", fill="both", expand=True)
        self.illustration = tk.Label(self.editor_frame, borderwidth=0)
        self.editor.bind("<<Modified>>", self.on_modified)
        self.editor.bind("<KeyRelease>", self.on_key_release, add=True)
        self.editor.bind("<ButtonRelease-1>", lambda _event: self.dismiss_autocomplete(), add=True)

        self.autocomplete = tk.Listbox(
            self.root, height=len(categories.CATEGORY_COMMANDS), width=15,
            exportselection=False, font=self.body_font, activestyle="none",
        )
        self.autocomplete_visible = False

    def _bind_keys(self):
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", self.leave_fullscreen)
        self.root.bind("<F9>", lambda _event: self.toggle_sidebar())
        self.root.bind("<Control-s>", self.save)
        self.root.bind("<Control-b>", lambda _event: self.format_selection("bold"))
        self.root.bind("<Control-i>", lambda _event: self.format_selection("italic"))
        self.root.bind("<Control-h>", lambda _event: self.format_selection("highlight"))
        self.root.bind("<Control-l>", lambda _event: self.toggle_bullets())
        self.root.bind("<Control-Left>", lambda _event: self.open_day(self.day - timedelta(days=1)))
        self.root.bind("<Control-Right>", lambda _event: self.open_day(self.day + timedelta(days=1)))
        self.root.bind("<Alt-Left>", lambda _event: self.change_calendar_month(-1))
        self.root.bind("<Alt-Right>", lambda _event: self.change_calendar_month(1))
        self.editor.bind("<Control-b>", lambda _event: self.format_selection("bold"))
        self.editor.bind("<Control-i>", lambda _event: self.format_selection("italic"))
        self.editor.bind("<Control-h>", lambda _event: self.format_selection("highlight"))
        self.editor.bind("<Control-l>", lambda _event: self.toggle_bullets())
        self.editor.bind("<Tab>", self.accept_autocomplete)
        self.editor.bind("<Return>", self.autocomplete_return)
        self.editor.bind("<Up>", lambda event: self.move_autocomplete(event, -1))
        self.editor.bind("<Down>", lambda event: self.move_autocomplete(event, 1))

    def apply_theme(self, name):
        if name not in THEMES:
            name = "dark"
        colors = THEMES[name]
        self.preferences["theme"] = name
        self.theme_box.set(name)
        self.root.configure(bg=colors["bg"])
        self.style.configure("TFrame", background=colors["bg"])
        self.style.configure("TLabel", background=colors["bg"], foreground=colors["text"])
        self.style.configure("TButton", background=colors["panel"], foreground=colors["text"], padding=4)
        self.style.map("TButton", background=[("active", colors["select"])])
        self.style.configure("TSeparator", background=colors["muted"])
        self.editor.configure(
            bg=colors["bg"], fg=colors["text"], insertbackground=colors["text"],
            selectbackground=colors["select"], selectforeground=colors["text"],
        )
        self.autocomplete.configure(
            bg=colors["panel"], fg=colors["text"], selectbackground=colors["select"],
            selectforeground=colors["text"], highlightbackground=colors["muted"],
        )
        self.editor.tag_configure("bold", font=self.bold_font)
        self.editor.tag_configure("italic", font=self.italic_font)
        self.editor.tag_configure("highlight", background=colors["highlight"])
        self.editor.tag_configure("category", foreground=colors["command"], font=self.bold_font)
        self.editor.tag_configure("marker", foreground=colors["muted"])
        self.illustration.configure(bg=colors["bg"])
        self.refresh_calendar()
        self.refresh_markup()
        settings.save(self.preferences)

    def set_fullscreen(self, enabled):
        try:
            self.root.attributes("-fullscreen", bool(enabled))
        except tk.TclError:
            enabled = False
        self.preferences["fullscreen"] = bool(enabled)

    def toggle_fullscreen(self, _event=None):
        self.set_fullscreen(not self.preferences["fullscreen"])
        settings.save(self.preferences)
        return "break"

    def leave_fullscreen(self, _event=None):
        if self.autocomplete_visible:
            self.dismiss_autocomplete()
        elif self.preferences["fullscreen"]:
            self.set_fullscreen(False)
            settings.save(self.preferences)
        return "break"

    def toggle_sidebar(self):
        if self.sidebar_open:
            self.sidebar.pack_forget()
        else:
            self.sidebar.pack(side="left", before=self.main, fill="y")
        self.sidebar_open = not self.sidebar_open
        self.preferences["sidebar_open"] = self.sidebar_open
        settings.save(self.preferences)

    def open_day(self, day, save_first=True):
        if save_first:
            self.save()
        self.dismiss_autocomplete()
        self.day = day
        self.calendar_day = day
        row = db.get_entry(self.connection, day)
        content = row["content"] if row else ""
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", content)
        self.editor.edit_reset()
        self.editor.edit_modified(False)
        self.dirty = False
        self.date_label.configure(text=day.strftime("%a, %d %b %Y"))
        self.status_label.configure(text="")
        self.refresh_markup()
        self.refresh_calendar()
        self.editor.focus_set()

    def save(self, _event=None):
        if self.save_job is not None:
            self.root.after_cancel(self.save_job)
            self.save_job = None
        if self.dirty:
            content = self.editor.get("1.0", "end-1c")
            db.save_entry(self.connection, self.day, content)
            self.dirty = False
            self.status_label.configure(text="Saved")
            self.refresh_calendar()
        return "break"

    def on_modified(self, _event=None):
        if not self.editor.edit_modified():
            return
        self.editor.edit_modified(False)
        self.dirty = True
        self.status_label.configure(text="Unsaved")
        if self.save_job is not None:
            self.root.after_cancel(self.save_job)
        self.save_job = self.root.after(self.AUTOSAVE_MS, self.save)
        self.refresh_markup()

    def refresh_markup(self):
        if not hasattr(self, "editor"):
            return
        for tag in ("bold", "italic", "highlight", "category", "marker"):
            self.editor.tag_remove(tag, "1.0", "end")
        text = self.editor.get("1.0", "end-1c")
        for block in categories.parse_blocks(text):
            if block.category is not None:
                line_number = block.start_line + 1
                self.editor.tag_add("category", f"{line_number}.0", f"{line_number}.end")
        for tag, pattern, marker_size in INLINE_PATTERNS:
            for match in pattern.finditer(text):
                inner_start = match.start() + marker_size
                inner_end = match.end() - marker_size
                self.editor.tag_add(tag, f"1.0+{inner_start}c", f"1.0+{inner_end}c")
                self.editor.tag_add("marker", f"1.0+{match.start()}c", f"1.0+{inner_start}c")
                self.editor.tag_add("marker", f"1.0+{inner_end}c", f"1.0+{match.end()}c")

    def format_selection(self, style):
        marker = text_editor.FORMAT_MARKERS[style]
        try:
            start, end = self.editor.index("sel.first"), self.editor.index("sel.last")
        except tk.TclError:
            self.status_label.configure(text="Select text first")
            return "break"
        selected = self.editor.get(start, end)
        self.editor.delete(start, end)
        self.editor.insert(start, text_editor.formatted_text(selected, style))
        self.editor.tag_add("sel", f"{start}+{len(marker)}c", f"{start}+{len(marker) + len(selected)}c")
        self.refresh_markup()
        return "break"

    def toggle_bullets(self):
        try:
            start = self.editor.index("sel.first linestart")
            end = self.editor.index("sel.last lineend")
        except tk.TclError:
            start = self.editor.index("insert linestart")
            end = self.editor.index("insert lineend")
        lines = self.editor.get(start, end).split("\n")
        replacement = "\n".join(text_editor.toggle_bullet_lines(lines))
        self.editor.delete(start, end)
        self.editor.insert(start, replacement)
        return "break"

    def on_key_release(self, event):
        if event.keysym in ("Up", "Down", "Return", "Tab", "Escape") and self.autocomplete_visible:
            return
        line_start = self.editor.index("insert linestart")
        before_cursor = self.editor.get(line_start, "insert")
        match = re.search(r"(?:^|\s)(/[A-Za-z]*)$", before_cursor)
        candidates = categories.matching_commands(match.group(1)) if match else ()
        if not candidates:
            self.dismiss_autocomplete()
            return
        self.autocomplete.delete(0, "end")
        for command in candidates:
            self.autocomplete.insert("end", command)
        self.autocomplete.selection_set(0)
        bbox = self.editor.bbox("insert")
        if bbox:
            x = self.editor.winfo_rootx() + bbox[0]
            y = self.editor.winfo_rooty() + bbox[1] + bbox[3]
            self.autocomplete.place(x=x - self.root.winfo_rootx(), y=y - self.root.winfo_rooty())
            self.autocomplete.lift()
            self.autocomplete_visible = True

    def move_autocomplete(self, _event, amount):
        if not self.autocomplete_visible:
            return None
        current = self.autocomplete.curselection()
        index = current[0] if current else 0
        index = max(0, min(self.autocomplete.size() - 1, index + amount))
        self.autocomplete.selection_clear(0, "end")
        self.autocomplete.selection_set(index)
        self.autocomplete.see(index)
        return "break"

    def accept_autocomplete(self, _event=None):
        if not self.autocomplete_visible:
            return None
        selection = self.autocomplete.curselection()
        if not selection:
            return "break"
        command = self.autocomplete.get(selection[0])
        line_start = self.editor.index("insert linestart")
        before_cursor = self.editor.get(line_start, "insert")
        match = re.search(r"(/[A-Za-z]*)$", before_cursor)
        if match:
            token_start = f"insert-{len(match.group(1))}c"
            self.editor.delete(token_start, "insert")
            self.editor.insert(token_start, command)
        self.dismiss_autocomplete()
        return "break"

    def autocomplete_return(self, event):
        if self.autocomplete_visible:
            self.accept_autocomplete(event)
            self.editor.insert("insert", "\n")
            return "break"
        line = self.editor.get("insert linestart", "insert lineend")
        if line.startswith("- "):
            if not line[2:].strip():
                self.editor.delete("insert linestart", "insert linestart+2c")
                self.editor.insert("insert", "\n")
            else:
                self.editor.insert("insert", "\n- ")
            return "break"
        return None

    def dismiss_autocomplete(self):
        if hasattr(self, "autocomplete"):
            self.autocomplete.place_forget()
        self.autocomplete_visible = False

    def change_calendar_month(self, amount):
        self.calendar_day = journal_calendar.change_month(self.calendar_day, amount)
        self.refresh_calendar()

    def refresh_calendar(self):
        if not hasattr(self, "calendar_buttons"):
            return
        colors = THEMES[self.preferences["theme"]]
        self.month_label.configure(text=self.calendar_day.strftime("%B %Y"))
        marked = db.entry_days(self.connection, self.calendar_day.year, self.calendar_day.month)
        weeks = journal_calendar.month_grid(self.calendar_day.year, self.calendar_day.month)
        cells = [day for week in weeks for day in week]
        cells.extend([None] * (42 - len(cells)))
        for index, button in enumerate(sum(self.calendar_buttons, [])):
            day = cells[index]
            if day is None:
                button.configure(text="", command=lambda: None, state="disabled", bg=colors["panel"])
                continue
            marker = "•" if day.day in marked else ""
            selected = day == self.day
            button.configure(
                text=f"{day.day}{marker}", command=lambda chosen=day: self.open_day(chosen),
                state="normal", bg=colors["select"] if selected else colors["panel"],
                fg=colors["text"], activebackground=colors["select"], activeforeground=colors["text"],
            )

    def choose_illustration(self):
        filename = filedialog.askopenfilename(
            parent=self.root, title="Choose a PNG illustration",
            filetypes=(("PNG image", "*.png"),),
        )
        if filename:
            self.load_illustration(filename)

    def load_illustration(self, filename, quiet=False):
        if not filename:
            return
        try:
            image = tk.PhotoImage(file=filename)
            max_width, max_height = 140, 120
            divisor = max(
                1,
                (image.width() + max_width - 1) // max_width,
                (image.height() + max_height - 1) // max_height,
            )
            if divisor > 1:
                image = image.subsample(divisor, divisor)
        except (tk.TclError, OSError) as error:
            if not quiet:
                messagebox.showerror("Illustration", f"Could not open that PNG.\n\n{error}", parent=self.root)
            return
        self.illustration_image = image
        self.illustration.configure(image=image)
        self.illustration.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-18)
        self.preferences["illustration"] = str(Path(filename))
        settings.save(self.preferences)

    def remove_illustration(self):
        self.illustration.place_forget()
        self.illustration.configure(image="")
        self.illustration_image = None
        self.preferences["illustration"] = ""
        settings.save(self.preferences)

    def close(self):
        self.save()
        settings.save(self.preferences)
        self.root.destroy()


def run(connection):
    root = tk.Tk()
    JournalApp(root, connection)
    root.mainloop()
