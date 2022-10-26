import os
import struct
from dataclasses import dataclass, InitVar
from io import BufferedReader
from pathlib import Path
from loguru import logger as log


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
        ) = struct.unpack("IIII", self.f.read(16))
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
        self.record_header_length = struct.unpack("I", self.f.read(4))[0]
        self.start_records_position = (
            self.pointer_records_region + self.record_header_length
        )
        self.f.seek(self.start_position)


@dataclass
class DatRecord:
    f: BufferedReader

    def __post_init__(self):
        identifier: bytes = self.f.read(2)
        self.identifier = ""
        self.text_identifier = ""
        self.record: bytes = bytearray()
        if identifier == b"\xfa\xfa":
            self.identifier = "FAFA"
        elif identifier == b"\xfd\xfd":
            self.identifier = "FDFD"
        elif identifier == b"\xbf\xfb":
            self.identifier = "BFFB"
        if self.identifier == "":
            self.f.tell()
        else:
            self.record_length, self.remaining_bytes = struct.unpack(
                "II", self.f.read(8)
            )

            if self.identifier == "FAFA" or self.identifier == "FDFD":
                pos = self.f.tell()
                self.f.seek(12, 1)
                (self.id, self.type_field) = struct.unpack("II", self.f.read(8))
                self._read_text_identifier()
                self.f.seek(pos)

            self.record: bytes = self.f.read(self.record_length - 10)

    def _read_text_identifier(self):
        end_found = False
        byte_array = b""
        while not end_found:
            # Keep reading until a null character is found
            b = self.f.read(2)
            if b == b"\x00\x00":
                end_found = True
            else:
                byte_array += b
        self.text_identifier = byte_array.decode("utf-16-le")


@dataclass
class DbExtract:
    filename: InitVar[str]

    def __post_init__(self, filename):
        self._filename = Path(filename)
        self._read()

    def _read_magic_number(self, f: BufferedReader):
        # if f.read(2) != b"\xfe\xff":
        #    raise RuntimeError("File isn't a Rockwell database (Dat) file")
        f.seek(0, 0)

    def _read_header(self, f: BufferedReader):
        self.header: DatHeader = DatHeader(f)

    def _read_records(self, f: BufferedReader):
        self.records = []
        f.seek(self.header.start_records_position)
        fafa = 0
        fdfd = 0
        bffb = 0

        for i in range(0, self.header.no_records + 1000):
            self.records.append(DatRecord(f))
            if self.records[i].identifier == "FAFA":
                fafa += 1
            elif self.records[i].identifier == "FDFD":
                fdfd += 1
            elif self.records[i].identifier == "BFFB":
                bffb += 1
            if self.records[i].identifier == "":
                break
        log.debug("f")

    def write_records_to_file(self, directory):
        Path(directory).mkdir(parents=True, exist_ok=True)
        for i in range(0, len(self.records)):
            self.records[i].text_identifier
            with open(
                os.path.join(
                    directory,
                    str(i)
                    + "-"
                    + self.records[i].identifier
                    + "-"
                    + self.records[i].text_identifier,
                ),
                "wb+",
            ) as out_file:
                log.debug("Write file - " + str(i) + "-" + self.records[i].identifier)
                out_file.write(self.records[i].record)
                out_file.flush()
                out_file.close()

    def _read(self):
        with open(self._filename, "rb") as f:
            # Check the file's magic number to confirm an DAT file
            self._read_magic_number(f)
            self._read_header(f)
            self._read_records(f)
            self.write_records_to_file("build/comps_records")
