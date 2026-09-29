"""Parse category blocks and subject tags from a daily journal entry.

Entries remain plain text in SQLite. This module is deliberately independent
from Tkinter and the database so its output can later feed normalized block and
tag tables without changing the editor.
"""

import re
from dataclasses import dataclass


CATEGORIES = ("memory", "reflection", "gratitude", "todo", "idea")
CATEGORY_COMMANDS = tuple("/" + category for category in CATEGORIES)

_COMMAND_RE = re.compile(
    r"^\s*/(" + "|".join(re.escape(category) for category in CATEGORIES) + r")\s*$",
    re.IGNORECASE,
)
_TAG_RE = re.compile(r"(?<![\w#])#([A-Za-z][A-Za-z0-9_-]*)")


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
    tags: tuple


def subject_tags(text):
    """Return unique, lower-case subject tags in first-seen order."""
    seen = set()
    result = []
    for match in _TAG_RE.finditer(text):
        tag = match.group(1).lower()
        if tag not in seen:
            seen.add(tag)
            result.append(tag)
    return tuple(result)


def parse_blocks(text):
    """Split plain entry text on recognized slash-command lines."""
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
                    tags=subject_tags(content),
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


def matching_commands(prefix):
    """Return autocomplete candidates for a slash-prefixed token."""
    normalized = prefix.lower()
    if not normalized.startswith("/"):
        return ()
    return tuple(command for command in CATEGORY_COMMANDS if command.startswith(normalized))
