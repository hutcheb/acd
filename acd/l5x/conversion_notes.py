"""Short notes about fallbacks taken while converting one ACD file.

When the converter replaces a failed read with a quiet fallback, it records
a note in the ConversionNotes owned by that conversion's ExportL5x. The notes
are written into the L5X as one XML comment, so someone reading the finished
file can tell "couldn't read" apart from "really empty".
"""

import re
from typing import Dict, List

from loguru import logger as log

# Characters that are illegal in XML 1.0.
XML_ILLEGAL_RE = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")
# XML forbids "--" inside a comment.
_DOUBLE_HYPHEN_RE = re.compile("-{2,}")


class ConversionNotes:
    """The notes recorded during one conversion, in the order they occurred."""

    # How many names a grouped note lists before "and N more".
    MAX_NAMES = 5

    def __init__(self) -> None:
        # A plain note, or the summary of a group whose names are in _groups.
        self._entries: List[str] = []
        self._groups: Dict[str, List[str]] = {}

    def add(self, note: str) -> None:
        """Record one plain-English note about a fallback."""
        self._entries.append(note)

    def warn(self, note: str, detail: str = "") -> None:
        """Log a warning and record the note. ``detail`` is logged only."""
        log.warning(f"{note} ({detail})" if detail else note)
        self._entries.append(note)

    def warn_grouped(self, summary: str, name: str, detail: str = "") -> None:
        """Log a warning and add ``name`` to the note for ``summary``.

        For a fallback that can hit many objects of one file: the notes get
        one line per summary, listing a few names and a count, instead of a
        line per object. The log still gets a line per object.
        """
        log.warning(f"{summary}: {name} ({detail})" if detail else f"{summary}: {name}")
        if summary not in self._groups:
            self._groups[summary] = []
            self._entries.append(summary)
        self._groups[summary].append(name)

    def current(self) -> List[str]:
        """Return a copy of the notes recorded so far."""
        notes = []
        for entry in self._entries:
            names = self._groups.get(entry)
            if names is None:
                notes.append(entry)
                continue
            shown = ", ".join(f"'{name}'" for name in names[: self.MAX_NAMES])
            more = len(names) - self.MAX_NAMES
            notes.append(f"{entry}: {shown}" + (f" and {more} more" if more > 0 else ""))
        return notes


def xml_comment(notes: List[str]) -> str:
    """Return the notes as one XML comment, or "" when there are none.

    Each note gets its own line. Line breaks, illegal XML characters and
    "--" runs are removed or replaced so the comment stays well-formed.
    """
    if not notes:
        return ""
    lines = []
    for note in notes:
        text = XML_ILLEGAL_RE.sub("", " ".join(note.splitlines()))
        lines.append(_DOUBLE_HYPHEN_RE.sub("-", text))
    return "<!-- acd-tools conversion notes:\n" + "\n".join(lines) + "\n-->\n"
