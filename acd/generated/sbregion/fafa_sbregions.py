# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 9):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class FafaSbregions(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.record_length = self._io.read_u4le()
        self.header = FafaSbregions.Header(self._io, self, self._root)
        self.len_record_buffer = self._io.read_u4le()
        self.record_buffer = self._io.read_bytes(self.len_record_buffer)

    class Header(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.sb_regions = self._io.read_u2le()
            self.identifier = self._io.read_u4le()
            self.language_type = (KaitaiStream.bytes_terminate(self._io.read_bytes(41), 0, False)).decode(u"UTF-8")



