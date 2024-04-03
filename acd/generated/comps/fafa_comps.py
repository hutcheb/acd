# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 9):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class FafaComps(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.record_length = self._io.read_u4le()
        self.header = FafaComps.Header(self._io, self, self._root)
        self.record_buffer = self._io.read_bytes(((self.record_length - 144) - 4))

    class Header(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.unknown_1 = self._io.read_u4le()
            self.seq_number = self._io.read_u2le()
            self.record_type = self._io.read_u2le()
            self.unknown_4 = self._io.read_u2le()
            self.unknown_5 = self._io.read_u2le()
            self.object_id = self._io.read_u4le()
            self.parent_id = self._io.read_u4le()
            self.record_name = (self._io.read_bytes(124)).decode(u"UTF-16")



