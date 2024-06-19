# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 9):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class FafaComents(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.record_length = self._io.read_u4le()
        self._raw_header = self._io.read_bytes(12)
        _io__raw_header = KaitaiStream(BytesIO(self._raw_header))
        self.header = FafaComents.Header(_io__raw_header, self, self._root)
        self.body = FafaComents.Body(self.header.string_start_position, self.lookup_id, self._io, self, self._root)

    class Header(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            pass

        @property
        def seq_number(self):
            if hasattr(self, '_m_seq_number'):
                return self._m_seq_number

            _pos = self._io.pos()
            self._io.seek(0)
            self._m_seq_number = self._io.read_u2le()
            self._io.seek(_pos)
            return getattr(self, '_m_seq_number', None)

        @property
        def string_length(self):
            if hasattr(self, '_m_string_length'):
                return self._m_string_length

            _pos = self._io.pos()
            self._io.seek(2)
            self._m_string_length = self._io.read_u2le()
            self._io.seek(_pos)
            return getattr(self, '_m_string_length', None)

        @property
        def string_start_position(self):
            if hasattr(self, '_m_string_start_position'):
                return self._m_string_start_position

            _pos = self._io.pos()
            self._io.seek(4)
            self._m_string_start_position = self._io.read_u2le()
            self._io.seek(_pos)
            return getattr(self, '_m_string_start_position', None)

        @property
        def record_type(self):
            if hasattr(self, '_m_record_type'):
                return self._m_record_type

            _pos = self._io.pos()
            self._io.seek(6)
            self._m_record_type = self._io.read_u2le()
            self._io.seek(_pos)
            return getattr(self, '_m_record_type', None)


    class Body(KaitaiStruct):
        def __init__(self, string_start_position, sub_record_type, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.string_start_position = string_start_position
            self.sub_record_type = sub_record_type
            self._read()

        def _read(self):
            pass

        @property
        def record_string_utf8(self):
            if hasattr(self, '_m_record_string_utf8'):
                return self._m_record_string_utf8

            if self.sub_record_type == 0:
                _pos = self._io.pos()
                self._io.seek(43)
                self._m_record_string_utf8 = (self._io.read_bytes_term(0, False, True, True)).decode(u"UTF-8")
                self._io.seek(_pos)

            return getattr(self, '_m_record_string_utf8', None)

        @property
        def record_string_utf16(self):
            if hasattr(self, '_m_record_string_utf16'):
                return self._m_record_string_utf16

            if self.sub_record_type == 1:
                _pos = self._io.pos()
                self._io.seek(46)
                self._m_record_string_utf16 = FafaComents.StrzUtf16(self._io, self, self._root)
                self._io.seek(_pos)

            return getattr(self, '_m_record_string_utf16', None)


    class StrzUtf16(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.value = (self._io.read_bytes((2 * (len(self.code_units) - 1)))).decode(u"utf-16le")
            self.term = self._io.read_u2le()
            if not self.term == 0:
                raise kaitaistruct.ValidationNotEqualError(0, self.term, self._io, u"/types/strz_utf_16/seq/1")

        @property
        def code_units(self):
            if hasattr(self, '_m_code_units'):
                return self._m_code_units

            _pos = self._io.pos()
            self._io.seek(self._io.pos())
            self._m_code_units = []
            i = 0
            while True:
                _ = self._io.read_u2le()
                self._m_code_units.append(_)
                if _ == 0:
                    break
                i += 1
            self._io.seek(_pos)
            return getattr(self, '_m_code_units', None)


    @property
    def lookup_id(self):
        if hasattr(self, '_m_lookup_id'):
            return self._m_lookup_id

        _pos = self._io.pos()
        self._io.seek(27)
        self._m_lookup_id = self._io.read_u2le()
        self._io.seek(_pos)
        return getattr(self, '_m_lookup_id', None)

    @property
    def sub_record_type(self):
        if hasattr(self, '_m_sub_record_type'):
            return self._m_sub_record_type

        _pos = self._io.pos()
        self._io.seek(41)
        self._m_sub_record_type = self._io.read_u2le()
        self._io.seek(_pos)
        return getattr(self, '_m_sub_record_type', None)


