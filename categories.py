"""Parse dynamic slash-command blocks from a daily journal entry.

Entries remain plain text in SQLite. Block types are parsed independently from
Tkinter and storage so they can later feed normalized block tables.
"""

import re
from dataclasses import dataclass


DEFAULT_BLOCK_TYPES = ("memory", "reflection", "gratitude", "todo", "idea")
_COMMAND_RE = re.compile(r"^\s*/([A-Za-z][A-Za-z0-9_-]*)\s*$")
_COMPLETED_COMMAND_RE = re.compile(
    r"^[ \t]*/([A-Za-z][A-Za-z0-9_-]*)[ \t]*(?=\n)", re.MULTILINE
)


@dataclass(frozen=True)
class JournalBlock:
    """One dynamically parsed section of an entry.

    ``category`` is ``None`` for text before the first slash command. Line
    numbers are zero-based and refer to the original entry, ready to become
    source metadata during a later structured-data migration.
    """

    category: object
    content: str
    start_line: int
    end_line: int


def parse_blocks(text):
    """Split entry text on any valid slash-command line."""
    lines = text.splitlines()
    if not lines:
        return []

    blocks = []
    category = None
    start_line = 0
    content_lines = []

    def append_block(end_line):
        content = "\n".join(content_lines)
        if category is not None or content:
            blocks.append(
                JournalBlock(
                    category=category,
                    content=content,
                    start_line=start_line,
                    end_line=end_line,
                )
            )

    for line_number, line in enumerate(lines):
        match = _COMMAND_RE.match(line)
        if match:
            append_block(line_number - 1)
            category = match.group(1).lower()
            start_line = line_number
            content_lines = []
        else:
            content_lines.append(line)

    append_block(len(lines) - 1)
    return blocks


def block_types_in_text(text):
    """Return unique completed block types in first-seen order.

    A type is registered only after its command line ends with Enter. This keeps
    autosave from persisting a partially typed name such as ``/ne``.
    """
    seen = set()
    result = []
    for match in _COMPLETED_COMMAND_RE.finditer(text):
        block_type = match.group(1).lower()
        if block_type not in seen:
            seen.add(block_type)
            result.append(block_type)
    return tuple(result)


def matching_commands(prefix, block_types=None):
    """Return autocomplete candidates from registered block types."""
    normalized = prefix.lower()
    if not normalized.startswith("/"):
        return ()
    available = block_types if block_types is not None else DEFAULT_BLOCK_TYPES
    commands = ("/" + block_type.lower().lstrip("/") for block_type in available)
    return tuple(command for command in commands if command.startswith(normalized))


def autocomplete_token(before_cursor, after_cursor=""):
    """Return ``(token, start_offset)`` for a completable token at the cursor.

    A block command occupies its own line, with optional leading whitespace.
    Completion is suppressed for inline or mid-command cursors, preventing a
    suggestion from replacing an unrelated slice of entry text.
    """
    if after_cursor[:1].isalnum() or after_cursor[:1] in ("_", "-"):
        return None
    match = re.match(r"^\s*(/[A-Za-z][A-Za-z0-9_-]*|/)$", before_cursor)
    if match is None:
        return None
    return match.group(1), match.start(1)


def blocks_for_type(entries, block_type):
    """Return ``(date, block)`` pairs matching a dynamic block type."""
    normalized = block_type.lstrip("/").lower()
    return tuple(
        (entry_date, block)
        for entry_date, content in entries
        for block in parse_blocks(content)
        if block.category == normalized
    )
