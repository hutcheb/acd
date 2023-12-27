import struct
from dataclasses import dataclass, InitVar
from io import BufferedReader
from pathlib import Path


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
    filename: InitVar[str]

    def __post_init__(self, filename):
        self._filename = Path(filename)
        self._read()

    def _read_magic_number(self, f: BufferedReader):
        f.seek(0, 0)

    def _read_header(self, f: BufferedReader):
        self.header: DatHeader = DatHeader(f)

    def _read_records(self, f: BufferedReader):
        self.records = []
        f.seek(self.header.start_records_position)

        for _ in range(0, self.header.no_records + self.header.no_records_table2):
            try:
                self.records.append(DatRecord(f))
            except:
                # TODO: Couldn't be bothered to figure out the end of file. Shame on me.
                pass

    def _read(self):
        with open(self._filename, "rb") as f:
            # Check the file's magic number to confirm an DAT file
            self._read_magic_number(f)
            self._read_header(f)
            self._read_records(f)
