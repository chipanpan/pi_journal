"""Small, terminal-independent text editor for journal entries."""

import re


FORMAT_MARKERS = {"bold": "**", "italic": "*", "highlight": "=="}

INLINE_PATTERNS = (
    ("bold_italic", re.compile(r"\*{3}(\S(?:[^\n]*?\S)?)\*{3}"), 3),
    (
        "bold",
        re.compile(r"(?<!\*)\*\*(?!\*)(\S(?:[^\n]*?\S)?)\*\*(?!\*)"),
        2,
    ),
    ("highlight", re.compile(r"==(\S(?:[^\n]*?\S)?)=="), 2),
    (
        "italic",
        re.compile(r"(?<!\*)\*(?!\*)(\S(?:[^\n]*?\S)?)\*(?!\*)"),
        1,
    ),
)


def formatted_text(text, style):
    """Wrap selected text in the plain-text marker for ``style``."""
    try:
        marker = FORMAT_MARKERS[style]
    except KeyError:
        raise ValueError("unknown formatting style: {}".format(style))
    return marker + text + marker


def has_format_markers(text_before, text_after, style):
    """Return whether a selection is immediately wrapped in ``style``."""
    try:
        marker = FORMAT_MARKERS[style]
    except KeyError:
        raise ValueError("unknown formatting style: {}".format(style))
    if style in ("bold", "italic"):
        left = len(text_before) - len(text_before.rstrip("*"))
        right = len(text_after) - len(text_after.lstrip("*"))
        wrapper_size = min(left, right)
        if style == "bold":
            return wrapper_size in (2, 3)
        return wrapper_size in (1, 3)
    return text_before.endswith(marker) and text_after.startswith(marker)


def toggle_bullet_lines(lines):
    """Add bullets to lines, or remove them when every nonempty line has one."""
    if lines == [""]:
        return ["- "]
    remove = bool(lines) and all(not line.strip() or line.startswith("- ") for line in lines)
    return [
        line[2:] if remove and line.startswith("- ") else (line if remove or not line else "- " + line)
        for line in lines
    ]


class Editor:
    def __init__(self, content=""):
        self.lines = content.split("\n")
        self.row = len(self.lines) - 1
        self.col = len(self.lines[self.row])

    @property
    def content(self):
        return "\n".join(self.lines)

    def handle(self, action, character=None):
        """Apply one key. Return True if the journal text changed."""
        line = self.lines[self.row]
        if action == "insert" and character and character.isprintable():
            self.lines[self.row] = line[:self.col] + character + line[self.col:]
            self.col += len(character)
            return True
        if action == "enter":
            self.lines[self.row:self.row + 1] = [line[:self.col], line[self.col:]]
            self.row += 1
            self.col = 0
            return True
        if action == "backspace":
            if self.col:
                self.lines[self.row] = line[:self.col - 1] + line[self.col:]
                self.col -= 1
            elif self.row:
                self.col = len(self.lines[self.row - 1])
                self.lines[self.row - 1] += self.lines.pop(self.row)
                self.row -= 1
            else:
                return False
            return True
        if action == "delete":
            if self.col < len(line):
                self.lines[self.row] = line[:self.col] + line[self.col + 1:]
            elif self.row < len(self.lines) - 1:
                self.lines[self.row] += self.lines.pop(self.row + 1)
            else:
                return False
            return True
        if action == "left":
            if self.col:
                self.col -= 1
            elif self.row:
                self.row -= 1
                self.col = len(self.lines[self.row])
        elif action == "right":
            if self.col < len(line):
                self.col += 1
            elif self.row < len(self.lines) - 1:
                self.row += 1
                self.col = 0
        elif action == "up":
            self.row = max(0, self.row - 1)
            self.col = min(self.col, len(self.lines[self.row]))
        elif action == "down":
            self.row = min(len(self.lines) - 1, self.row + 1)
            self.col = min(self.col, len(self.lines[self.row]))
        elif action == "home":
            self.col = 0
        elif action == "end":
            self.col = len(line)
        return False

    def visual_rows(self, width):
        """Word-wrap text and locate the cursor in the resulting rows.

        Spaces and existing hyphens are preferred as wrap points. A single word
        wider than the pane still has to be split so every row fits on screen.
        """
        width = max(1, width)
        rows = []
        cursor = (0, 0)
        for logical_row, line in enumerate(self.lines):
            base = len(rows)
            segments = self._wrap_line(line, width)
            rows.extend(line[start:end] for start, end in segments)
            if logical_row == self.row:
                for visual_row, (start, end) in enumerate(segments):
                    if self.col < end or visual_row == len(segments) - 1:
                        cursor = (base + visual_row, self.col - start)
                        break
        return rows, cursor

    @staticmethod
    def _wrap_line(line, width):
        """Return contiguous slices, preferring breaks after spaces/hyphens."""
        if not line:
            return [(0, 0)]

        segments = []
        start = 0
        while len(line) - start > width:
            limit = start + width
            window = line[start:limit]
            space = max(window.rfind(" "), window.rfind("\t"))
            hyphen = window.rfind("-")
            break_at = max(space, hyphen)
            if break_at >= 0:
                end = start + break_at + 1
            else:
                end = limit
            segments.append((start, end))
            start = end

        segments.append((start, len(line)))
        if len(line) == start + width:
            # Keep a visible cursor position after a completely full final row.
            segments.append((len(line), len(line)))
        return segments
