import re
import struct
from dataclasses import dataclass
from sqlite3 import Cursor

from acd.dbextract import DatRecord
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

        if r.header.language_type == "Rung NT":
            text = r.record_buffer.decode("utf-16-le").rstrip('\x00')
            self.text = self.replace_tag_references(text)

            query: str = "INSERT INTO rungs VALUES (?, ?, ?)"
            entry: tuple = (
                r.header.identifier, self.text, '')
            self._cur.execute(query, entry)
        elif r.header.language_type == "REGION AST":
            pass
        else:
            pass


    def replace_tag_references(self, sb_rec):
        m = re.findall("@[A-Za-z0-9]*@", sb_rec)
        for tag in m:
            tag_no = tag[1:-1]
            tag_id = int(tag_no, 16)
            self._cur.execute("SELECT object_id, comp_name FROM comps WHERE object_id=" + str(tag_id))
            results = self._cur.fetchall()
            sb_rec = sb_rec.replace(tag, results[0][1])
        return sb_rec
