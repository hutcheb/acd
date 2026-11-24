import re
import struct
from dataclasses import dataclass
from sqlite3 import Cursor
from typing import Dict, Optional

from loguru import logger as log

from acd.database.dbextract import DatRecord

from acd.generated.sbregion.fafa_sbregions import FafaSbregions


@dataclass
class SbRegionRecord:
    _cur: Cursor
    dat_record: DatRecord

    def __post_init__(self):
        if self.dat_record.identifier == 64250:
            r = FafaSbregions.from_bytes(self.dat_record.record.record_buffer)
        else:
            return

        if r.header.language_type == "Rung NT" or r.header.language_type == "REGION NT":
            text = r.record_buffer.decode("utf-16-le").rstrip("\x00")
            self.text = self.replace_tag_references(text)
            self._cur.execute("INSERT INTO rungs VALUES (?, ?, ?)", (r.header.identifier, self.text, ""))
        elif r.header.language_type == "REGION AST":
            pass
        elif r.header.language_type == "REGION LE UID":
            uuid = struct.unpack("<I", r.record_buffer[-4:])[0]
            pass

    def replace_tag_references(self, sb_rec):
        for tag in re.findall("@[A-Za-z0-9]*@", sb_rec):
            tag_id = int(tag[1:-1], 16)
            self._cur.execute(
                "SELECT object_id, comp_name FROM comps WHERE object_id=" + str(tag_id)
            )
            results = self._cur.fetchall()
            if len(results) == 0:
                return sb_rec
            sb_rec = sb_rec.replace(tag, results[0][1])
        return sb_rec

    @staticmethod
    def parse(dat_record: DatRecord, name_lookup: Dict[int, str]) -> Optional[tuple]:
        if dat_record.identifier != 64250:
            return None
        r = FafaSbregions.from_bytes(dat_record.record.record_buffer)
        if r.header.language_type not in ("Rung NT", "REGION NT"):
            return None
        try:
            text = r.record_buffer.decode("utf-16-le").rstrip("\x00")
        except UnicodeDecodeError:
            # Source-protected routines (e.g. AOIs with source protection
            # enabled) store encrypted bytes here rather than UTF-16 text.
            # Skip the record so the rest of the project still converts.
            log.warning(
                f"Skipping SbRegion record {r.header.identifier} "
                f"({r.header.language_type}): content is not UTF-16 text, "
                f"routine is likely source protected"
            )
            return None
        for tag in re.findall("@[A-Za-z0-9]*@", text):
            tag_id = int(tag[1:-1], 16)
            name = name_lookup.get(tag_id)
            if name is None:
                break
            text = text.replace(tag, name)
        return (r.header.identifier, text, "")
