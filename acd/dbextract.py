import struct
from dataclasses import dataclass, InitVar
from io import BufferedReader
from pathlib import Path

from acd.generated.dat import Dat


@dataclass
class DatHeader:
    f: BufferedReader

    def __post_init__(self):
        self.start_position = self.f.seek(8)
        (
            self.total_length,
            self.region_pointer_offset,
            self._unknown1,
            self.no_records,
            self.no_records_table2,
        ) = struct.unpack("IIIII", self.f.read(20))
        self.f.seek(self.region_pointer_offset)
        if self.f.read(2) != b"\xfe\xfe":
            raise RuntimeError("Pointer Region Incorrect")
        (
            self.region_pointer_length,
            self.unknown2,
            self._unknown3,
            self.pointer_metadata_region,
            self.pointer_records_region,
        ) = struct.unpack("IIIII", self.f.read(20))
        self.f.seek(self.pointer_records_region)
        if self.f.read(2) != b"\xfe\xfe":
            raise RuntimeError("Record Region Incorrect")
        self.record_header_length, self._unknown4, self.unknown5, self.record_format = struct.unpack("IIII", self.f.read(16))
        if self.record_format == 132:
            raise RuntimeError("Cross Reference Databases Not Supported")
        elif self.record_format != 512:
            raise RuntimeError("Unknown record format")
        self.start_records_position = (
            self.pointer_records_region + self.record_header_length
        )
        self.f.seek(self.start_position)


@dataclass
class DatRecord:
    f: BufferedReader

    def __post_init__(self):
        self.identifier: bytes = self.f.read(2)
        self.record: bytes = bytearray()

        self.record_length = struct.unpack("I", self.f.read(4))[0]
        self.record: bytes = self.f.read(self.record_length - 6)


@dataclass
class DbExtract:
    filename: str

    def read(self) -> Dat:
        return Dat.from_file(self.filename)
