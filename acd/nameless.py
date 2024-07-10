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
        if self.dat_record.identifier == 64250:
            identifier_offset = 8
            self.identifier = struct.unpack(
                "I", self.dat_record.record.record_buffer[identifier_offset : identifier_offset + 4]
            )[0]

            object_identifier_offset = 0x0C
            self.object_identifier = struct.unpack_from("<I", self.dat_record.record.record_buffer, object_identifier_offset)[0]

            query: str = "INSERT INTO nameless VALUES (?, ?, ?)"
            enty: tuple = (self.object_identifier, self.identifier, self.dat_record.record.record_buffer)
            self._cur.execute(query, enty)
