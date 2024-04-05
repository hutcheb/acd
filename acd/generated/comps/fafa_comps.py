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
            pass

        @property
        def record_type(self):
            if hasattr(self, '_m_record_type'):
                return self._m_record_type

            _pos = self._io.pos()
            self._io.seek(6)
            self._m_record_type = self._io.read_u2le()
            self._io.seek(_pos)
            return getattr(self, '_m_record_type', None)

        @property
        def object_id(self):
            if hasattr(self, '_m_object_id'):
                return self._m_object_id

            _pos = self._io.pos()
            self._io.seek(16)
            self._m_object_id = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_object_id', None)

        @property
        def record_name(self):
            if hasattr(self, '_m_record_name'):
                return self._m_record_name

            _pos = self._io.pos()
            self._io.seek(24)
            self._m_record_name = (self._io.read_bytes(124)).decode(u"UTF-16")
            self._io.seek(_pos)
            return getattr(self, '_m_record_name', None)

        @property
        def seq_number(self):
            if hasattr(self, '_m_seq_number'):
                return self._m_seq_number

            _pos = self._io.pos()
            self._io.seek(4)
            self._m_seq_number = self._io.read_u2le()
            self._io.seek(_pos)
            return getattr(self, '_m_seq_number', None)

        @property
        def parent_id(self):
            if hasattr(self, '_m_parent_id'):
                return self._m_parent_id

            _pos = self._io.pos()
            self._io.seek(20)
            self._m_parent_id = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_parent_id', None)



