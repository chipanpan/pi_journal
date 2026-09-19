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
        """Wrap text at screen width and locate the cursor in wrapped rows."""
        width = max(1, width)
        rows = []
        cursor = (0, 0)
        for logical_row, line in enumerate(self.lines):
            base = len(rows)
            # Include an empty final segment when the cursor is just past a full line.
            rows.extend(line[start:start + width] for start in range(0, len(line) + 1, width))
            if logical_row == self.row:
                cursor = (base + self.col // width, self.col % width)
        return rows, cursor
