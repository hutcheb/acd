import struct
from dataclasses import dataclass
from sqlite3 import Cursor

from acd.dbextract import DatRecord
from acd.generated.comps.fafa_comps import FafaComps
from acd.generated.comps.fdfd_comps import FdfdComps


@dataclass
class RecordData:
    object_id: int
    record_length: int
    seq_number: int
    record_type: int
    dat_record: DatRecord


@dataclass
class CompsRecord:
    _cur: Cursor
    dat_record: DatRecord

    def __post_init__(self):

        if self.dat_record.identifier == 64250:
            fafa_comps = FafaComps.from_bytes(self.dat_record.record.record_buffer)
            self.seq_number = fafa_comps.header.seq_number
            self.record_type = fafa_comps.header.record_type
            self.object_id = fafa_comps.header.object_id
            self.parent_id = fafa_comps.header.parent_id
            self.text = fafa_comps.header.record_name

            query: str = "INSERT INTO comps VALUES (?, ?, ?, ?, ?, ?)"
            enty: tuple = (self.object_id, self.parent_id, self.text, self.seq_number, self.record_type, fafa_comps.record_buffer)
            self._cur.execute(query, enty)


        elif self.dat_record.identifier == 65021:
            # Pointer to Data record
            fdfd_comps = FdfdComps.from_bytes(self.dat_record.record.record_buffer)
            self.seq_number = fafa_comps.header.seq_number
            self.record_type = fafa_comps.header.record_type
            self.object_id = fafa_comps.header.object_id
            self.parent_id = fafa_comps.header.parent_id
            self.text = fafa_comps.header.record_name

            query: str = "INSERT INTO comps VALUES (?, ?, ?, ?, ?, ?)"
            enty: tuple = (
            self.object_id, self.parent_id, self.text, self.seq_number, self.record_type, fafa_comps.record_buffer)
            self._cur.execute(query, enty)

        else:
            self.text = ""
            self.object_id = -1


