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
        self.file_size = self.f.seek(-8, 2) + 8
        self.no_files, self._unknown_two = struct.unpack("II", self.f.read(8))
        self.record_offset = self.file_size - self.no_files * 528 - 8
        self.f.seek(0, 0)


@dataclass
class FileRecord:
    f: BufferedReader

    def __post_init__(self):
        end_found = False
        byte_array = b''
        count = 0
        while not end_found:
            b = self.f.read(2)
            if b == b'\x00\x00':
                end_found = True
            else:
                byte_array += b
        filename_length = len(byte_array)
        self.filename = byte_array.decode('utf-16-le')
        self.f.seek(520 - filename_length - 2, 1)
        self.file_length, self.file_offset = struct.unpack("II", self.f.read(8))
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
        self.records = []
        for i in range(0, self.header.no_files):
            self.records.append(FileRecord(f))

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

