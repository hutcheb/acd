import re
import struct
from dataclasses import dataclass
from sqlite3 import Cursor

from acd.dbextract import DatRecord
from acd.generated.comments.fafa_coments import FafaComents


@dataclass
class CommentsRecord:
    _cur: Cursor
    dat_record: DatRecord

    def __post_init__(self):
        if self.dat_record.identifier == 64250:
            r = FafaComents.from_bytes(self.dat_record.record.record_buffer)
            pass
        else:
            return

        query: str = "INSERT INTO comments VALUES (?, ?, ?, ?, ?, ?)"
        if r.header.record_type == 0x04:
            pass
        try:
            entry: tuple = (
                r.header.seq_number,
                r.header.sub_record_length,
                r.body.object_id,
                r.body.record_string,
                r.header.record_type,
                r.header.parent)
        except Exception as e:
            pass
        self._cur.execute(query, entry)

    def replace_tag_references(self, sb_rec):
        m = re.findall("@[A-Za-z0-9]*@", sb_rec)
        for tag in m:
            tag_no = tag[1:-1]
            tag_id = int(tag_no, 16)
            self._cur.execute("SELECT object_id, comp_name FROM comps WHERE object_id=" + str(tag_id))
            results = self._cur.fetchall()
            sb_rec = sb_rec.replace(tag, results[0][1])
        return sb_rec
