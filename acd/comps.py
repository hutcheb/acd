import struct
from dataclasses import dataclass
from io import BytesIO
from sqlite3 import Cursor

from kaitaistruct import KaitaiStream

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
            r = FafaComps.from_bytes(self.dat_record.record.record_buffer)
        elif self.dat_record.identifier == 65021:
            r = FdfdComps(self.dat_record.record_length, KaitaiStream(BytesIO(self.dat_record.record.record_buffer)))
        else:
            return

        query: str = f"DELETE FROM comps WHERE object_id={r.header.object_id}"
        self._cur.execute(query)

        query: str = "INSERT INTO comps VALUES (?, ?, ?, ?, ?, ?)"
        ss = r.header.record_name.value
        entry: tuple = (
            r.header.object_id, r.header.parent_id, r.header.record_name.value, r.header.seq_number, r.header.record_type,
            r.record_buffer)
        self._cur.execute(query, entry)
