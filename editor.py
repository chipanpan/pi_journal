"""Small, terminal-independent text editor for journal entries."""


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
