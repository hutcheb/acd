import binascii
import struct
from dataclasses import dataclass, InitVar
from io import BufferedReader
from pathlib import Path
from loguru import logger as log

@dataclass
class AcdHeader:
    f: BufferedReader

    def __post_init__(self):
        self.f.seek(-16, 2)
        self.preamble_len, self.record_offset, self.no_files, self._unknown_two = struct.unpack("IIII", self.f.read(16))
        self.f.seek(0, 0)


@dataclass
class FileRecord:
    f: BufferedReader
    start_offset: int

    def __post_init__(self):
        self.f.seek(self.start_offset, 0)
        filename_record = self.f.read(520)
        filename_length = filename_record.find(b'\x00\x00')
        self.filename = filename_record[:filename_length + 1].decode('utf-16-le')
        pass


@dataclass
class Unzip:
    filename: InitVar[str]

    def __post_init__(self, filename):
        self._filename = Path(filename)
        self._read()

    def _read_magic_number(self, f: BufferedReader):
        magicBytes = binascii.hexlify(f.read(2))
        if magicBytes != b'0d0a':
            log.debug("")
            raise RuntimeError("File isn't a Rockwell ACD file")
        f.seek(0, 0)

    def _read_file_header(self, f: BufferedReader):
        self.header: AcdHeader = AcdHeader(f)

    def _read_records(self, f: BufferedReader):
        f.seek(self.header.record_offset)
        self._preamble = f.read(self.header.preamble_len)
        self.records = []
        for i in range(0, self.header.no_files):
            self.records.append(FileRecord(f, self.header.record_offset + self.header.preamble_len))

    def _read(self):
        with open(self._filename, 'rb') as f:
            # Check the file's magic number to confirm an ACD file
            self._read_magic_number(f)
            self._read_file_header(f)
            self._read_records(f)


    def get_number_of_files(self) -> int:
        return self.header.no_files

    def get_file_header_offset(self):
        return self.header.record_offset

