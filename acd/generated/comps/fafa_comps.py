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
            self._raw__m_record_name = self._io.read_bytes(124)
            _io__raw__m_record_name = KaitaiStream(BytesIO(self._raw__m_record_name))
            self._m_record_name = FafaComps.Unicode16(_io__raw__m_record_name, self, self._root)
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


    class Unicode16(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            if self.start_ >= 0:
                self.first = self._io.read_bytes(0)

            self.c = []
            i = 0
            while True:
                _ = self._io.read_u2le()
                self.c.append(_)
                if _ == 0:
                    break
                i += 1
            if self.end_ >= 0:
                self.last = self._io.read_bytes(0)


        @property
        def start_(self):
            if hasattr(self, '_m_start_'):
                return self._m_start_

            self._m_start_ = self._io.pos()
            return getattr(self, '_m_start_', None)

        @property
        def end_(self):
            if hasattr(self, '_m_end_'):
                return self._m_end_

            self._m_end_ = self._io.pos()
            return getattr(self, '_m_end_', None)

        @property
        def as_string(self):
            if hasattr(self, '_m_as_string'):
                return self._m_as_string

            _pos = self._io.pos()
            self._io.seek(self.start_)
            self._m_as_string = (self._io.read_bytes(((self.end_ - self.start_) - 2))).decode(u"UTF-16")
            self._io.seek(_pos)
            return getattr(self, '_m_as_string', None)



