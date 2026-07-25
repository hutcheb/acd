import struct
from dataclasses import dataclass
from io import BytesIO
from sqlite3 import Cursor
from typing import Optional

from acd.database.dbextract import DatRecord
from kaitaistruct import KaitaiStream

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
        entry = CompsRecord.parse(self.dat_record)
        if entry is None:
            return
        self._cur.execute(f"DELETE FROM comps WHERE object_id={entry[0]}")
        self._cur.execute("INSERT INTO comps VALUES (?, ?, ?, ?, ?, ?)", entry)

    @staticmethod
    def parse(dat_record: DatRecord) -> Optional[tuple]:
        raw = bytes(dat_record.record.record_buffer)

        # The v20 Comps layout omits the reserved four bytes at offset 0x0C
        # that are present in newer files. In that layout, the nonzero object
        # ID occupies the reserved field and shifts the remaining header and
        # payload four bytes earlier.
        if dat_record.identifier in (64250, 65021) and struct.unpack_from(
            "<I", raw, 0x0C
        )[0] != 0:
            object_id, parent_id = struct.unpack_from("<II", raw, 0x0C)
            name_buffer = raw[0x14:0x90]
            name_length = next(
                (
                    index
                    for index in range(0, len(name_buffer) - 1, 2)
                    if name_buffer[index : index + 2] == b"\0\0"
                ),
                len(name_buffer),
            )
            record_name = name_buffer[:name_length].decode(
                "utf-16-le", errors="replace"
            )
            seq_offset = 0x08 if dat_record.identifier == 64250 else 0x04
            seq_number = struct.unpack_from("<H", raw, seq_offset)[0]
            record_type = struct.unpack_from("<H", raw, 0x0A)[0]

            if dat_record.identifier == 64250:
                payload_start = 0x90
                payload_end = struct.unpack_from("<I", raw, 0)[0]
                # Legacy FAFA lengths stop four bytes before the physical
                # record. Those bytes contain the end of the final Rx
                # attribute, so retain them when that exact trailer exists.
                if record_name == "Region Map" and payload_end + 4 <= len(raw):
                    payload_end += 4
                elif payload_end + 4 == len(raw):
                    payload_end += 4
            else:
                payload_start = 0x97
                payload_end = dat_record.len_record - 8

            if payload_end < payload_start or payload_end > len(raw):
                raise ValueError("Invalid legacy Comps record length")

            return (
                object_id,
                parent_id,
                record_name,
                seq_number,
                record_type,
                raw[payload_start:payload_end],
            )

        if dat_record.identifier == 64250:
            r = FafaComps.from_bytes(raw)
        elif dat_record.identifier == 65021:
            r = FdfdComps(
                dat_record.len_record,
                KaitaiStream(BytesIO(raw)),
            )
        else:
            return None
        return (
            r.header.object_id,
            r.header.parent_id,
            r.header.record_name.value,
            r.header.seq_number,
            r.header.record_type,
            r.record_buffer,
        )
