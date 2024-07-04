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
        self._raw_header = self._io.read_bytes(10)
        _io__raw_header = KaitaiStream(BytesIO(self._raw_header))
        self.header = FafaComents.Header(_io__raw_header, self, self._root)
        _on = self.header.record_type
        if _on == 14:
            self._raw_body = self._io.read_bytes((self.record_length - 10))
            _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
            self.body = FafaComents.Utf16Record(12, _io__raw_body, self, self._root)
        elif _on == 4:
            self._raw_body = self._io.read_bytes((self.record_length - 10))
            _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
            self.body = FafaComents.Utf16Record(12, _io__raw_body, self, self._root)
        elif _on == 1:
            self._raw_body = self._io.read_bytes((self.record_length - 10))
            _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
            self.body = FafaComents.AsciiRecord(_io__raw_body, self, self._root)
        elif _on == 13:
            self._raw_body = self._io.read_bytes((self.record_length - 10))
            _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
            self.body = FafaComents.Utf16Record(12, _io__raw_body, self, self._root)
        elif _on == 3:
            self._raw_body = self._io.read_bytes((self.record_length - 10))
            _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
            self.body = FafaComents.Utf16Record(12, _io__raw_body, self, self._root)
        elif _on == 23:
            self._raw_body = self._io.read_bytes((self.record_length - 10))
            _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
            self.body = FafaComents.ControllerRecord(_io__raw_body, self, self._root)
        elif _on == 2:
            self._raw_body = self._io.read_bytes((self.record_length - 10))
            _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
            self.body = FafaComents.AsciiRecord(_io__raw_body, self, self._root)
        elif _on == 25:
            self._raw_body = self._io.read_bytes((self.record_length - 10))
            _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
            self.body = FafaComents.ControllerRecord(_io__raw_body, self, self._root)
        else:
            self.body = self._io.read_bytes((self.record_length - 10))

    class ControllerRecord(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.unknown_1 = self._io.read_bytes(8)
            self.object_id = self._io.read_u4le()
            self.unknown_2 = self._io.read_bytes(4)
            self.tag_reference = FafaComents.StrzUtf16(self._io, self, self._root)
            self.unknown_3 = self._io.read_bytes(12)
            self.record_string = (self._io.read_bytes_term(0, False, True, True)).decode(u"UTF-8")


    class AsciiRecord(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.unknown_1 = self._io.read_bytes(13)
            self.object_id = self._io.read_u4le()
            self.unknown_2 = self._io.read_bytes(13)
            self.record_string = (self._io.read_bytes_term(0, False, True, True)).decode(u"UTF-8")


    class AsciiRecord4(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.unknown_1 = self._io.read_bytes(8)
            self.object_id = self._io.read_u4le()
            self.unknown_2 = self._io.read_bytes(24)
            self.record_string = (self._io.read_bytes_term(0, False, True, True)).decode(u"UTF-8")


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
        def record_type(self):
            if hasattr(self, '_m_record_type'):
                return self._m_record_type

            _pos = self._io.pos()
            self._io.seek(2)
            self._m_record_type = self._io.read_u2le()
            self._io.seek(_pos)
            return getattr(self, '_m_record_type', None)

        @property
        def sub_record_length(self):
            if hasattr(self, '_m_sub_record_length'):
                return self._m_sub_record_length

            _pos = self._io.pos()
            self._io.seek(4)
            self._m_sub_record_length = self._io.read_u2le()
            self._io.seek(_pos)
            return getattr(self, '_m_sub_record_length', None)

        @property
        def parent(self):
            if hasattr(self, '_m_parent'):
                return self._m_parent

            _pos = self._io.pos()
            self._io.seek(6)
            self._m_parent = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_parent', None)


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


    class Utf16Record(KaitaiStruct):
        def __init__(self, zero_buffer_length, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.zero_buffer_length = zero_buffer_length
            self._read()

        def _read(self):
            self.unknown_1 = self._io.read_bytes(8)
            self.object_id = self._io.read_u4le()
            self.unknown_2 = self._io.read_bytes(4)
            self.len_record = self._io.read_u2le()
            self.tag_reference = FafaComents.StrzUtf16(self._io, self, self._root)
            self.unknown_3 = self._io.read_bytes(self.zero_buffer_length)
            self.record_string = (self._io.read_bytes_term(0, False, True, True)).decode(u"UTF-8")


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


