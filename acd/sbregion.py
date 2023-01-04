import struct
from dataclasses import dataclass

from acd.dbextract import DatRecord


@dataclass
class SbRegionRecord:
    dat_record: DatRecord

    def __post_init__(self):
        identifier_offset = 2
        self.identifier = struct.unpack(
            "I", self.dat_record.record[identifier_offset : identifier_offset + 4]
        )[0]
        language_type_record_length: int = 29
        language_type_offset: int = 6
        self.language_type = (
            self.dat_record.record[
                language_type_offset : language_type_offset
                + language_type_record_length
            ]
            .decode("utf-8")
            .split("\x00")[0]
        )
        record_length_offset = 47
        self.record_length = struct.unpack(
            "I", self.dat_record.record[record_length_offset : record_length_offset + 4]
        )[0]
        record_offset = 51
        self.text = self.dat_record.record[
            record_offset : record_offset + self.record_length - 2
        ].decode("utf-16-le")
