"""Keyboard-first Tkinter interface for the daily journal."""

import tkinter as tk
from datetime import date, timedelta
from tkinter import font as tkfont, ttk

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
        "bg": "#b8aa8d", "panel": "#9f9177", "text": "#302a22",
        "muted": "#625846", "accent": "#654631", "select": "#7f7059",
        "highlight": "#897542", "command": "#6c3f2d",
    },
}

class JournalApp:
    AUTOSAVE_MS = 900
    AUTOCOMPLETE_START = "autocomplete_start"
    AUTOCOMPLETE_END = "autocomplete_end"

    def __init__(self, root, connection):
        self.root = root
        self.connection = connection
        self.preferences = settings.load()
        self.day = date.today()
        self.calendar_day = self.day
        self.dirty = False
        self.save_job = None
        self.active_block_type = None
        self.sidebar_open = bool(self.preferences["sidebar_open"])
        self._build_window()
        self._build_styles()
        self._build_ui()
        if not self.sidebar_open:
            self.sidebar.pack_forget()
        self._bind_keys()
        self.apply_theme(self.preferences["theme"])
        self.set_fullscreen(bool(self.preferences["fullscreen"]))
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
        self.bold_italic_font = tkfont.Font(
            family=body_family, size=13, weight="bold", slant="italic"
        )
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
        self.month_label = ttk.Label(month_bar, anchor="center", font=self.bold_font)
        self.month_label.pack(fill="x", expand=True)

        self.weekday_frame = ttk.Frame(self.sidebar)
        self.weekday_frame.pack(fill="x", pady=(7, 1))
        self.weekday_labels = []
        for column, label in enumerate(("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")):
            self.weekday_frame.columnconfigure(column, weight=1)
            weekday = tk.Label(
                self.weekday_frame, text=label, anchor="center", borderwidth=0,
                padx=0, pady=1, font=self.small_font,
            )
            weekday.grid(row=0, column=column, sticky="ew")
            self.weekday_labels.append(weekday)

        self.calendar_frame = ttk.Frame(self.sidebar)
        self.calendar_frame.pack(fill="x")
        for column in range(7):
            self.calendar_frame.columnconfigure(column, weight=1)
        self.calendar_cells = []
        for row in range(6):
            row_cells = []
            for column in range(7):
                cell = tk.Label(
                    self.calendar_frame, width=3, relief="flat", borderwidth=0,
                    padx=0, pady=1, font=self.small_font,
                )
                cell.grid(row=row, column=column, sticky="nsew")
                row_cells.append(cell)
            self.calendar_cells.append(row_cells)

        ttk.Separator(self.sidebar).pack(fill="x", pady=6)
        ttk.Label(self.sidebar, text="Block types", font=self.bold_font).pack(fill="x")
        self.block_types_list = tk.Listbox(
            self.sidebar, height=5, selectmode=tk.SINGLE, exportselection=False,
            borderwidth=0, highlightthickness=0, activestyle="none",
            font=self.small_font,
        )
        self.block_types_list.pack(fill="x", pady=(2, 4))
        self.block_types_list.bind("<Up>", lambda event: self.move_block_type(event, -1))
        self.block_types_list.bind("<Down>", lambda event: self.move_block_type(event, 1))
        self.block_types_list.bind("<Return>", self.select_block_type)
        self.block_types_list.bind("<ButtonRelease-1>", self.select_block_type)

        self.sidebar_hint = ttk.Label(
            self.sidebar,
            text=(
                "F6 theme · F7 types · F9 sidebar\n"
                "F11 full · Ctrl+Q quit"
            ),
            justify="left", font=self.small_font,
        )
        self.sidebar_hint.pack(side="bottom", anchor="w")

        self.main = ttk.Frame(self.container, padding=(14, 10, 14, 8))
        self.main.pack(side="left", fill="both", expand=True)

        header = ttk.Frame(self.main)
        header.pack(fill="x", pady=(0, 8))
        self.date_label = ttk.Label(header, font=self.title_font)
        self.date_label.pack(side="left", fill="x", expand=True)
        self.status_label = ttk.Label(header, text="", font=self.small_font)
        self.status_label.pack(side="right", padx=8)

        self.editor_frame = ttk.Frame(self.main)
        self.editor_frame.pack(fill="both", expand=True)
        self.editor = tk.Text(
            self.editor_frame, wrap="word", undo=True, autoseparators=True,
            maxundo=100, borderwidth=0, padx=10, pady=10,
            font=self.body_font, insertwidth=2,
        )
        self.editor.pack(fill="both", expand=True)
        self.editor.bind("<<Modified>>", self.on_modified)
        self.editor.bind("<KeyRelease>", self.on_key_release, add=True)
        self.editor.bind("<ButtonRelease-1>", lambda _event: self.dismiss_autocomplete(), add=True)

        self.autocomplete = tk.Listbox(
            self.root, height=5, width=15,
            exportselection=False, font=self.body_font, activestyle="none",
        )
        self.autocomplete_visible = False

    def _bind_keys(self):
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<F6>", self.cycle_theme)
        self.root.bind("<F7>", self.focus_block_types)
        self.root.bind("<Escape>", self.leave_fullscreen)
        self.root.bind("<F9>", lambda _event: self.toggle_sidebar())
        self.root.bind("<Control-q>", self.close)
        self.root.bind("<Control-s>", self.save)
        self.root.bind("<Control-b>", lambda _event: self.format_selection("bold"))
        self.root.bind("<Control-i>", lambda _event: self.format_selection("italic"))
        self.root.bind("<Control-h>", lambda _event: self.format_selection("highlight"))
        self.root.bind("<Control-l>", lambda _event: self.toggle_bullets())
        self.root.bind("<Control-Left>", lambda _event: self.open_day(self.day - timedelta(days=1)))
        self.root.bind("<Control-Right>", lambda _event: self.open_day(self.day + timedelta(days=1)))
        self.root.bind("<Control-Up>", lambda _event: self.open_day(self.day - timedelta(days=7)))
        self.root.bind("<Control-Down>", lambda _event: self.open_day(self.day + timedelta(days=7)))
        self.root.bind("<Control-t>", self.open_today)
        self.root.bind("<Alt-Left>", lambda _event: self.change_calendar_month(-1))
        self.root.bind("<Alt-Right>", lambda _event: self.change_calendar_month(1))
        self.editor.bind("<Control-b>", lambda _event: self.format_selection("bold"))
        self.editor.bind("<Control-i>", lambda _event: self.format_selection("italic"))
        self.editor.bind("<Control-h>", lambda _event: self.format_selection("highlight"))
        self.editor.bind("<Control-l>", lambda _event: self.toggle_bullets())
        self.editor.bind("<Control-q>", self.close)
        self.editor.bind("<Control-t>", self.open_today)
        self.editor.bind("<Tab>", self.accept_autocomplete)
        self.editor.bind("<Return>", self.autocomplete_return)
        self.editor.bind("<Up>", lambda event: self.move_autocomplete(event, -1))
        self.editor.bind("<Down>", lambda event: self.move_autocomplete(event, 1))

    def apply_theme(self, name):
        if name not in THEMES:
            name = "dark"
        colors = THEMES[name]
        self.preferences["theme"] = name
        self.root.configure(bg=colors["bg"])
        self.style.configure("TFrame", background=colors["bg"])
        self.style.configure("TLabel", background=colors["bg"], foreground=colors["text"])
        self.style.configure("TSeparator", background=colors["muted"])
        self.editor.configure(
            bg=colors["bg"], fg=colors["text"], insertbackground=colors["text"],
            selectbackground=colors["select"], selectforeground=colors["text"],
        )
        self.autocomplete.configure(
            bg=colors["panel"], fg=colors["text"], selectbackground=colors["select"],
            selectforeground=colors["text"], highlightbackground=colors["muted"],
        )
        self.block_types_list.configure(
            bg=colors["bg"], fg=colors["text"],
            selectbackground=colors["select"], selectforeground=colors["text"],
        )
        self.editor.tag_configure("bold", font=self.bold_font)
        self.editor.tag_configure("italic", font=self.italic_font)
        self.editor.tag_configure("bold_italic", font=self.bold_italic_font)
        self.editor.tag_configure("highlight", background=colors["highlight"])
        self.editor.tag_configure("category", foreground=colors["command"], font=self.bold_font)
        # Formatting remains portable plain text in SQLite, while Tk hides the
        # storage markers and renders only the formatted content.
        self.editor.tag_configure("marker", elide=True)
        self.refresh_calendar()
        self.refresh_markup()
        settings.save(self.preferences)

    def cycle_theme(self, _event=None):
        names = tuple(THEMES)
        current = self.preferences.get("theme", names[0])
        next_name = names[(names.index(current) + 1) % len(names)] if current in names else names[0]
        self.apply_theme(next_name)
        self.status_label.configure(text="{} theme".format(next_name.title()))
        return "break"

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
        elif self.active_block_type is not None:
            self.open_day(self.day)
        elif self.root.focus_get() == self.block_types_list:
            self.editor.focus_set()
            self.status_label.configure(text="")
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
        self.active_block_type = None
        if hasattr(self, "block_types_list"):
            self.block_types_list.selection_clear(0, "end")
        row = db.get_entry(self.connection, day)
        content = row["content"] if row else ""
        self.editor.configure(state="normal")
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", content)
        self.editor.edit_reset()
        self.editor.edit_modified(False)
        self.dirty = False
        self.date_label.configure(text=day.strftime("%a, %d %b %Y"))
        self.status_label.configure(text="")
        self.refresh_markup()
        self.refresh_calendar()
        self.refresh_block_types()
        self.editor.focus_set()

    def open_today(self, _event=None):
        self.open_day(date.today())
        return "break"

    def save(self, _event=None):
        if self.save_job is not None:
            self.root.after_cancel(self.save_job)
            self.save_job = None
        if self.dirty and self.active_block_type is None:
            content = self.editor.get("1.0", "end-1c")
            db.save_entry(self.connection, self.day, content)
            self.dirty = False
            self.status_label.configure(text="Saved")
            self.refresh_calendar()
            self.refresh_block_types()
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
        for tag in (
            "bold", "italic", "bold_italic", "highlight", "category", "marker"
        ):
            self.editor.tag_remove(tag, "1.0", "end")
        text = self.editor.get("1.0", "end-1c")
        for block in categories.parse_blocks(text):
            if block.category is not None:
                line_number = block.start_line + 1
                self.editor.tag_add("category", f"{line_number}.0", f"{line_number}.end")
        for tag, pattern, marker_size in text_editor.INLINE_PATTERNS:
            for match in pattern.finditer(text):
                inner_start = match.start() + marker_size
                inner_end = match.end() - marker_size
                self.editor.tag_add(tag, f"1.0+{inner_start}c", f"1.0+{inner_end}c")
                self.editor.tag_add("marker", f"1.0+{match.start()}c", f"1.0+{inner_start}c")
                self.editor.tag_add("marker", f"1.0+{inner_end}c", f"1.0+{match.end()}c")

    def refresh_block_types(self):
        if not hasattr(self, "block_types_list"):
            return
        block_types = db.block_types(self.connection)
        self.block_types_list.delete(0, "end")
        for block_type in block_types:
            self.block_types_list.insert("end", "/" + block_type)
        if self.active_block_type in block_types:
            index = block_types.index(self.active_block_type)
            self.block_types_list.selection_set(index)
            self.block_types_list.activate(index)
            self.block_types_list.see(index)

    def focus_block_types(self, _event=None):
        if not self.sidebar_open:
            self.toggle_sidebar()
        if self.block_types_list.size() == 0:
            return "break"
        index = self.block_types_list.curselection()
        index = index[0] if index else 0
        self.block_types_list.selection_clear(0, "end")
        self.block_types_list.selection_set(index)
        self.block_types_list.activate(index)
        self.block_types_list.see(index)
        self.block_types_list.focus_set()
        self.status_label.configure(text="↑/↓ move · Enter select")
        return "break"

    def move_block_type(self, _event, amount):
        if self.block_types_list.size() == 0:
            return "break"
        selection = self.block_types_list.curselection()
        index = selection[0] if selection else 0
        index = max(0, min(self.block_types_list.size() - 1, index + amount))
        self.block_types_list.selection_clear(0, "end")
        self.block_types_list.selection_set(index)
        self.block_types_list.activate(index)
        self.block_types_list.see(index)
        return "break"

    def select_block_type(self, _event=None):
        selection = self.block_types_list.curselection()
        if not selection:
            return "break"
        block_type = self.block_types_list.get(selection[0]).lstrip("/")
        if block_type == self.active_block_type:
            return "break"
        self.show_block_type_results(block_type)
        return "break"

    def show_block_type_results(self, block_type):
        self.save()
        entries = (
            (row["date"], row["content"]) for row in db.all_entries(self.connection)
        )
        matches = categories.blocks_for_type(entries, block_type)

        sections = []
        for entry_date, block in matches:
            heading = date.fromisoformat(entry_date).strftime("%d %b %Y")
            if block.category is not None:
                heading += " · " + block.category
            sections.append("— {} —\n{}".format(heading, block.content))

        self.active_block_type = block_type
        self.refresh_block_types()
        self.dismiss_autocomplete()
        self.editor.configure(state="normal")
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", "\n\n".join(sections) if sections else "No matching blocks.")
        self.editor.edit_reset()
        self.editor.edit_modified(False)
        self.dirty = False
        self.date_label.configure(text="/{} · {} blocks".format(block_type, len(matches)))
        self.status_label.configure(text="Esc: daily entry")
        self.refresh_markup()
        self.editor.configure(state="disabled")

    def format_selection(self, style):
        marker = text_editor.FORMAT_MARKERS[style]
        try:
            start, end = self.editor.index("sel.first"), self.editor.index("sel.last")
        except tk.TclError:
            self.status_label.configure(text="Select text first")
            return "break"
        selected = self.editor.get(start, end)
        selected_chars = self.editor.count(start, end, "chars")[0]
        marker_size = len(marker)
        marker_start = self.editor.index(f"{start}-{marker_size}c")
        marker_end = self.editor.index(f"{end}+{marker_size}c")
        context_start = self.editor.index(f"{start}-3c")
        context_end = self.editor.index(f"{end}+3c")
        text_before = self.editor.get(context_start, start)
        text_after = self.editor.get(end, context_end)

        if text_editor.has_format_markers(text_before, text_after, style):
            # Remove the closing marker first so the opening deletion cannot
            # shift its index. In ***text*** this removes only the requested
            # layer, leaving the other bold/italic marker intact.
            self.editor.delete(end, marker_end)
            self.editor.delete(marker_start, start)
            selection_start = marker_start
        else:
            self.editor.insert(end, marker)
            self.editor.insert(start, marker)
            selection_start = self.editor.index(f"{start}+{marker_size}c")

        selection_end = self.editor.index(f"{selection_start}+{selected_chars}c")
        self.editor.tag_add("sel", selection_start, selection_end)
        self.editor.mark_set("insert", selection_end)
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
        # These keys either operate the popup or deliberately dismiss it. Do
        # not immediately reopen it from the corresponding key-release event.
        if event.keysym in ("Up", "Down", "Return", "Tab", "Escape"):
            return
        line_start = self.editor.index("insert linestart")
        before_cursor = self.editor.get(line_start, "insert")
        after_cursor = self.editor.get("insert", "insert lineend")
        context = categories.autocomplete_token(before_cursor, after_cursor)
        candidates = (
            categories.matching_commands(context[0], db.block_types(self.connection))
            if context else ()
        )
        if not candidates:
            self.dismiss_autocomplete()
            return

        token, start_offset = context
        token_start = f"{line_start}+{start_offset}c"
        self.editor.mark_set(self.AUTOCOMPLETE_START, token_start)
        self.editor.mark_gravity(self.AUTOCOMPLETE_START, tk.LEFT)
        self.editor.mark_set(self.AUTOCOMPLETE_END, "insert")
        self.editor.mark_gravity(self.AUTOCOMPLETE_END, tk.RIGHT)

        self.autocomplete.delete(0, "end")
        self.autocomplete.configure(height=min(6, len(candidates)))
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
        else:
            self.dismiss_autocomplete()

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
        try:
            token_start = self.editor.index(self.AUTOCOMPLETE_START)
            token_end = self.editor.index(self.AUTOCOMPLETE_END)
        except tk.TclError:
            self.dismiss_autocomplete()
            return "break"

        typed_token = self.editor.get(token_start, token_end)
        registered = db.block_types(self.connection)
        if command not in categories.matching_commands(typed_token, registered):
            self.dismiss_autocomplete()
            return "break"

        self.editor.delete(token_start, token_end)
        self.editor.insert(token_start, command)
        self.editor.mark_set("insert", f"{token_start}+{len(command)}c")
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
        if hasattr(self, "editor"):
            self.editor.mark_unset(self.AUTOCOMPLETE_START, self.AUTOCOMPLETE_END)
        self.autocomplete_visible = False

    def change_calendar_month(self, amount):
        self.open_day(journal_calendar.change_month(self.day, amount))

    def refresh_calendar(self):
        if not hasattr(self, "calendar_cells"):
            return
        colors = THEMES[self.preferences["theme"]]
        self.month_label.configure(text=self.calendar_day.strftime("%B %Y"))
        marked = db.entry_days(self.connection, self.calendar_day.year, self.calendar_day.month)
        for index, weekday in enumerate(self.weekday_labels):
            weekday.configure(
                bg=colors["panel"],
                fg=colors["text"],
            )
        weeks = journal_calendar.month_grid(self.calendar_day.year, self.calendar_day.month)
        cells = [day for week in weeks for day in week]
        cells.extend([None] * (42 - len(cells)))
        for index, cell in enumerate(sum(self.calendar_cells, [])):
            day = cells[index]
            if day is None:
                cell.configure(text="", bg=colors["bg"])
                continue
            marker = "•" if day.day in marked else ""
            cell.configure(
                text=f"{day.day}{marker}",
                bg=colors["select"] if day == self.day else colors["bg"],
                fg=colors["text"],
            )

    def close(self, _event=None):
        self.save()
        settings.save(self.preferences)
        self.root.destroy()
        return "break"


def run(connection):
    root = tk.Tk()
    JournalApp(root, connection)
    root.mainloop()
