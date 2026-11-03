"""st_decoder.py — Production ST routine decoder for Rockwell .ACD files.

Extracts ordered Structured Text (ST) source from the Nameless.Dat binary
entirely from the ACD's internal structure — no L5X export or ground truth needed.

Algorithm
---------
The ordering information is in an "index record" — a packed little-endian
array of 4-byte object_ids that list line records in correct source order.

Full chain from a routine's comps object_id to its ordered source:

    routine comps id                   (in Comps.Dat)
      → descriptor                     (nameless row, parent_id = routine comps id, ~38 bytes)
        → aspect                       (nameless row, parent_id = descriptor, ~40 bytes)
          → index record               (nameless row, parent_id = aspect, larger; its own
                                        object_id appears as parent_id for line records)
            → line text records        (nameless rows, parent_id = index record oid)

Each index record's payload starting at byte 22 is a packed list of 4-byte
little-endian object_ids referencing the line records in correct source order.

Public API
----------
    from st_decoder import STDecoder
    dec = STDecoder(exp)           # exp = ExportL5x instance
    routines = dec.all_routines()  # list of (name, comps_id, lines)
    lines = dec.decode(comps_id)   # ordered list of str, or None
"""
from __future__ import annotations
import struct
import re
from collections import defaultdict
from typing import Optional


# ── Low-level helpers ────────────────────────────────────────────────────────

def _decode_line_text(rec: bytes, name_lookup: dict) -> Optional[str]:
    """Extract the UTF-16LE string from a line-record blob.

    Marker: b'\\xff\\xfe\\xff', then 1-byte length (in UTF-16 code units),
    then length*2 bytes of UTF-16-LE text.
    Tag references encoded as @hex_id@ are resolved via name_lookup.
    Returns None if the record carries no text payload.
    """
    idx = rec.find(b"\xff\xfe\xff")
    if idx == -1 or idx + 4 > len(rec):
        return None
    length = rec[idx + 3]
    sb = rec[idx + 4: idx + 4 + length * 2]
    if len(sb) < length * 2:
        return None
    try:
        text = sb.decode("utf-16-le")
    except Exception:
        return None
    for tag in re.findall(r"@[0-9a-f]+@", text):
        tid = int(tag[1:-1], 16)
        nm = name_lookup.get(tid)
        if nm:
            text = text.replace(tag, nm)
    return text


def _decode_index_record(idx_rec: bytes, line_recs: dict[int, bytes],
                          name_lookup: dict) -> list[str]:
    """Resolve and order the line texts referenced by an index record.

    idx_rec layout:
      bytes  0-19: header (length, flags, parent_id, self oid, type constant)
      bytes 20-21: 2 padding/flag bytes
      bytes 22-  : packed little-endian uint32 object_ids, one per source line

    Notes:
    - The index record may reference the same object_id more than once (a
      Rockwell compiler artifact, e.g. for FOR loop body unrolling).  Since the
      same record object can only represent one logical statement, duplicate
      oid references are skipped after the first occurrence.
    - Entries whose oid does not resolve to a known line record are skipped;
      these reference sub-group anchors or compiled-form records that are not
      direct children of this index record.

    Returns a list of decoded strings (blank lines are preserved as '').
    """
    out: list[str] = []
    seen: set[int] = set()
    off = 22
    while off + 4 <= len(idx_rec):
        oid = struct.unpack_from("<I", idx_rec, off)[0]
        off += 4
        if oid in seen:
            continue  # duplicate index entry — same line object referenced twice
        seen.add(oid)
        rec = line_recs.get(oid)
        if rec is None:
            continue  # references a sub-group anchor or out-of-scope record
        text = _decode_line_text(rec, name_lookup)
        if text is not None:
            out.append(text)
    return out


# ── Core decoder ─────────────────────────────────────────────────────────────

class STDecoder:
    """Decode ordered ST source for all routines in an ACD file.

    Parameters
    ----------
    exp : ExportL5x
        An already-opened ExportL5x object (hutcheb/acd).
        The decoder does NOT close it; the caller is responsible.
    """

    def __init__(self, exp):
        self._name_lookup: dict[int, str] = exp._id_to_name
        cur = exp._cur

        # ── Load full nameless table into memory once ──────────────────────
        cur.execute("SELECT object_id, parent_id, record FROM nameless ORDER BY rowid")
        rows = [(int(oid), int(pid), bytes(rec))
                for oid, pid, rec in cur.fetchall()]

        # Forward and reverse maps
        self._oid_to_pid: dict[int, int] = {oid: pid for oid, pid, _ in rows}
        self._oid_to_rec: dict[int, bytes] = {oid: rec for oid, _, rec in rows}
        self._children: dict[int, list[int]] = defaultdict(list)
        for oid, pid, _ in rows:
            self._children[pid].append(oid)

        # A "group id" is any nameless object_id that also appears as a parent_id
        # AND has its own record.  These are both container anchors (index records)
        # and content-group parents.
        all_pids = set(self._oid_to_pid.values())
        self._index_record_ids: set[int] = {
            oid for oid in self._oid_to_rec if oid in all_pids
        }

        # Comps object_id set — used to root the chain
        cur.execute("SELECT object_id FROM comps")
        self._comps_ids: set[int] = {int(r[0]) for r in cur.fetchall()}

        # Cache: comps_id → ordered lines (populated lazily)
        self._cache: dict[int, Optional[list[str]]] = {}

    # ── Public ───────────────────────────────────────────────────────────────

    def all_routines(self) -> list[tuple[str, int, list[str]]]:
        """Return (name, comps_id, lines) for every ST routine in the ACD.

        Routines are discovered entirely from the ACD's internal structure —
        no L5X or tag-name hints required.  Routines whose ST content cannot
        be decoded are silently omitted (they would have no index record).
        """
        results = []
        seen_comps: set[int] = set()

        for desc_oid, desc_pid, _ in (
            (oid, self._oid_to_pid[oid], None)
            for oid in self._oid_to_rec
            if self._oid_to_pid.get(oid) in self._comps_ids
        ):
            comps_id = desc_pid
            if comps_id in seen_comps:
                continue
            lines = self._decode_from_desc(desc_oid)
            if lines is not None:
                seen_comps.add(comps_id)
                name = self._name_lookup.get(comps_id, f"<{comps_id}>")
                self._cache[comps_id] = lines
                results.append((name, comps_id, lines))

        return sorted(results, key=lambda t: t[0])

    def decode(self, comps_id: int) -> Optional[list[str]]:
        """Return the ordered ST source lines for one routine by its comps object_id.

        Returns None if the routine has no decodable ST content.
        """
        if comps_id in self._cache:
            return self._cache[comps_id]

        # Find the descriptor(s) whose parent_id == comps_id
        for desc_oid in self._children.get(comps_id, []):
            if desc_oid not in self._oid_to_rec:
                continue
            lines = self._decode_from_desc(desc_oid)
            if lines is not None:
                self._cache[comps_id] = lines
                return lines

        self._cache[comps_id] = None
        return None

    # ── Private ──────────────────────────────────────────────────────────────

    def _decode_from_desc(self, desc_oid: int) -> Optional[list[str]]:
        """Walk aspects → index records under desc_oid; return the best decoded lines."""
        best: Optional[list[str]] = None

        for asp_oid in self._children.get(desc_oid, []):
            for child_oid in self._children.get(asp_oid, []):
                if child_oid not in self._index_record_ids:
                    continue
                idx_rec = self._oid_to_rec.get(child_oid, b"")
                # Gather grandchildren (the actual line-text records)
                line_recs = {
                    gc: self._oid_to_rec[gc]
                    for gc in self._children.get(child_oid, [])
                    if gc in self._oid_to_rec
                }
                decoded = _decode_index_record(idx_rec, line_recs, self._name_lookup)
                if decoded and (best is None or len(decoded) > len(best)):
                    best = decoded

        return best if best else None
