import struct
from dataclasses import dataclass
from sqlite3 import Cursor

from acd.dbextract import DatRecord

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

        if self.dat_record.identifier == b'\xfa\xfa':
            # Data record
            record_length_offset = 0
            self.record_length = struct.unpack(
                "I", self.dat_record.record[0 : record_length_offset + 4]
            )[0]

            seq_number_offset = 8
            self.seq_number = struct.unpack(
                "H", self.dat_record.record[seq_number_offset: seq_number_offset + 2]
            )[0]

            record_type_offset = 10
            self.record_type = struct.unpack(
                "H", self.dat_record.record[record_type_offset: record_type_offset + 2]
            )[0]

            object_id_offset = 16
            self.object_id = struct.unpack(
                "I", self.dat_record.record[object_id_offset : object_id_offset + 4]
            )[0]

            parent_id_offset = 20
            self.parent_id = struct.unpack(
                "I", self.dat_record.record[parent_id_offset: parent_id_offset + 4]
            )[0]

            text_offset = 24
            self.text = self.dat_record.record[
                        text_offset: text_offset + 124
                        ].decode("utf-16-le").split("\x00")[0]

            query: str = "INSERT INTO comps VALUES (?, ?, ?, ?, ?, ?)"
            enty: tuple = (self.object_id, self.parent_id, self.text, self.seq_number, self.record_type, self.dat_record.record)
            self._cur.execute(query, enty)


        elif self.dat_record.identifier == b'\xfd\xfd':
            # Pointer to Data record
            seq_number_offset = 8
            self.seq_number = struct.unpack(
                "H", self.dat_record.record[seq_number_offset: seq_number_offset + 2]
            )[0]

            record_type_offset = 10
            self.record_type = struct.unpack(
                "H", self.dat_record.record[record_type_offset: record_type_offset + 2]
            )[0]

            object_id_offset = 16
            self.object_id = struct.unpack(
                "I", self.dat_record.record[object_id_offset: object_id_offset + 4]
            )[0]

            parent_id_offset = 20
            self.parent_id = struct.unpack(
                "I", self.dat_record.record[parent_id_offset: parent_id_offset + 4]
            )[0]

            text_offset = 24
            self.text = self.dat_record.record[
                        text_offset: text_offset + 124
                        ].decode("utf-16-le").split("\x00")[0]

            query: str = "INSERT INTO pointers VALUES (?, ?, ?, ?, ?, ?)"
            enty: tuple = (self.object_id, self.parent_id, self.text, self.seq_number, self.record_type, self.dat_record.record)
            self._cur.execute(query, enty)

        else:
            self.text = ""
            self.object_id = -1


