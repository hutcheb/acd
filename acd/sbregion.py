import re
import struct
from dataclasses import dataclass
from sqlite3 import Cursor

from acd.dbextract import DatRecord


@dataclass
class SbRegionRecord:
    _cur: Cursor
    dat_record: DatRecord

    def __post_init__(self):
        if self.dat_record.identifier == b'\xfa\xfa':
            record_length_offset = 0
            self.record_length = struct.unpack(
                "I", self.dat_record.record[0: record_length_offset + 4]
            )[0]

            identifier_offset = 6
            self.identifier = struct.unpack(
                "I", self.dat_record.record[identifier_offset : identifier_offset + 4]
            )[0]
            language_type_record_length: int = 29
            language_type_offset: int = 10
            self.language_type = (
                self.dat_record.record[
                    language_type_offset : language_type_offset
                    + language_type_record_length
                ]
                .decode("utf-8")
                .split("\x00")[0]
            )
            record_length_offset = 51
            self.record_length = struct.unpack(
                "I", self.dat_record.record[record_length_offset : record_length_offset + 4]
            )[0]

            if self.language_type == "Rung NT":
                record_offset = 55
                self.text = self.dat_record.record[
                    record_offset : record_offset + self.record_length - 2
                ].decode("utf-16-le")

                self.text = self.replace_tag_references(self.text)

                query: str = "INSERT INTO rungs VALUES ('" + str(self.identifier) + "', '" + self.text + "', '')"
                self._cur.execute(query)
            elif self.language_type == "REGION AST":
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
