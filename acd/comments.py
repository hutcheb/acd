import re
import struct
from dataclasses import dataclass
from sqlite3 import Cursor

from acd.dbextract import DatRecord


@dataclass
class CommentsRecord:
    _cur: Cursor
    dat_record: DatRecord

    def __post_init__(self):
        if self.dat_record.identifier == b'\xfa\xfa':
            record_length_offset = 0
            self.record_length = struct.unpack(
                "I", self.dat_record.record[0: record_length_offset + 4]
            )[0]

            not_sure_offset = 6
            self.not_sure = struct.unpack(
                "H", self.dat_record.record[not_sure_offset: not_sure_offset + 2]
            )[0]

            length_offset = 8
            self.length = struct.unpack(
                "H", self.dat_record.record[length_offset: length_offset + 2]
            )[0]

            identifier_offset = 10
            self.identifier = struct.unpack(
                "I", self.dat_record.record[identifier_offset : identifier_offset + 4]
            )[0]

            seq_no_offset = 27
            self.seq_no = struct.unpack(
                "I", self.dat_record.record[seq_no_offset: seq_no_offset + 4]
            )[0]

            record_type_offset = 32
            self.record_type = struct.unpack(
                "I", self.dat_record.record[record_type_offset: record_type_offset + 4]
            )[0]

            if self.record_type == 0:
                text_offset = 44
                self.text = self.dat_record.record[
                            text_offset: -1
                            ].decode("ascii").split("\x00")[0]
            else:
                self.text = ""


            query: str = "INSERT INTO comments VALUES (?, ?, ?, ?, ?, ?, ?)"
            enty: tuple = (self.identifier, self.not_sure, self.length, self.text, self.seq_no, self.record_type, self.dat_record.record)
            self._cur.execute(query, enty)

    def replace_tag_references(self, sb_rec):
        m = re.findall("@[A-Za-z0-9]*@", sb_rec)
        for tag in m:
            tag_no = tag[1:-1]
            tag_id = int(tag_no, 16)
            self._cur.execute("SELECT object_id, comp_name FROM comps WHERE object_id=" + str(tag_id))
            results = self._cur.fetchall()
            sb_rec = sb_rec.replace(tag, results[0][1])
        return sb_rec
