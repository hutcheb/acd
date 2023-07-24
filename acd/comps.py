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
class CompsTag(RecordData):

    def __post_init__(self):
        data_type_offset = 214
        data_type_int = struct.unpack(
            "B", self.dat_record.record[data_type_offset: data_type_offset + 1]
        )[0]

        if data_type_int == 129:
            self.data_type = "CONTROL"
        elif data_type_int == 130:
            self.data_type = "COUNTER"
        elif data_type_int == 131:
            self.data_type = "TIMER"
        elif data_type_int == 132:
            self.data_type = "PID"
        elif data_type_int == 135:
            self.data_type = "135"
        elif data_type_int == 193:
            self.data_type = "BOOL"
        elif data_type_int == 194:
            self.data_type = "SINT"
        elif data_type_int == 195:
            self.data_type = "INT"
        elif data_type_int == 196:
            self.data_type = "DINT"
        elif data_type_int == 197:
            self.data_type = "LINT"
        elif data_type_int == 198:
            self.data_type = "USINT"
        elif data_type_int == 199:
            self.data_type = "UINT"
        elif data_type_int == 200:
            self.data_type = "UDINT"
        elif data_type_int == 201:
            self.data_type = "LWORD"
        elif data_type_int == 202:
            self.data_type = "REAL"
        elif data_type_int == 203:
            self.data_type = "LREAL"
        elif data_type_int == 206:
            self.data_type = "STRING"
        else:
            self.data_type = None

        array_length_offest = 215
        self.array_length = struct.unpack(
            "B", self.dat_record.record[array_length_offest: array_length_offest + 1]
        )[0]

        if self.data_type is not None and self.array_length != 0:
            self.data_type = self.data_type + "[" + str(self.array_length) + "]"

        comment_length_offset = 238
        self.comment_length = struct.unpack(
            "B", self.dat_record.record[comment_length_offset: comment_length_offset + 1]
        )[0]

        comment_start_offset = 240
        if self.comment_length > 0:
            self.text = self.dat_record.record[
                        comment_start_offset: comment_start_offset + self.comment_length
                        ].decode("ascii")
            if self.text == "Dint_Conv":
                pass
        else:
            self.text = ""




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


