import re
import struct
from dataclasses import dataclass
from sqlite3 import Cursor

from acd.dbextract import DatRecord


@dataclass
class NamelessRecord:
    _cur: Cursor
    dat_record: DatRecord

    def __post_init__(self):
        if self.dat_record.identifier == b'\xfa\xfa':
            identifier_offset = 8
            self.identifier = struct.unpack(
                "I", self.dat_record.record[identifier_offset : identifier_offset + 4]
            )[0]

            not_sure_offset = 12
            self.not_sure = struct.unpack(
                "I", self.dat_record.record[not_sure_offset: not_sure_offset + 4]
            )[0]

            query: str = "INSERT INTO nameless VALUES (?, ?, ?)"
            enty: tuple = (self.identifier, self.not_sure, self.dat_record.record)
            self._cur.execute(query, enty)
