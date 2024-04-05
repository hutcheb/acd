# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 9):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class Database(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.header = Database.Header(self._io, self, self._root)
        self._raw_records = self._io.read_bytes(((self.header.file_length - self.header.first_record_position) + 1))
        _io__raw_records = KaitaiStream(BytesIO(self._raw_records))
        self.records = Database.Records(_io__raw_records, self, self._root)

    class FefeRecord(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.record_length = self._io.read_u4le()
            self.blank_1 = self._io.read_u4le()
            self.unknown_1 = self._io.read_u4le()
            self.unknown_2 = self._io.read_u4le()
            self.record_buffer = []
            for i in range(self.record_length):
                self.record_buffer.append(self._io.read_u1())



    class Header(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.format_type = self._io.read_u4le()
            self.blank_2 = self._io.read_u4le()
            self.file_length = self._io.read_u4le()
            self.first_record_position = self._io.read_u4le()
            self.blank_3 = self._io.read_u4le()
            self.number_records_fafa = self._io.read_u4le()
            self.header_buffer = []
            for i in range((self.first_record_position - 24)):
                self.header_buffer.append(self._io.read_u1())



    class Records(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.record = []
            i = 0
            while not self._io.is_eof():
                self.record.append(Database.Record(self._io, self, self._root))
                i += 1



    class Record(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.record_header = self._io.read_u2le()
            if not  ((self.record_header == 65278) or (self.record_header == 65021) or (self.record_header == 64250) or (self.record_header == 64447)) :
                raise kaitaistruct.ValidationNotAnyOfError(self.record_header, self._io, u"/types/record/seq/0")
            self.record_length = self._io.read_u4le()
            _on = self.record_header
            if _on == 64250:
                self._raw_record_buffer = self._io.read_bytes((self.record_length - 6))
                _io__raw_record_buffer = KaitaiStream(BytesIO(self._raw_record_buffer))
                self.record_buffer = Database.FafaRecord(_io__raw_record_buffer, self, self._root)
            elif _on == 65278:
                self._raw_record_buffer = self._io.read_bytes((self.record_length - 6))
                _io__raw_record_buffer = KaitaiStream(BytesIO(self._raw_record_buffer))
                self.record_buffer = Database.FefeRecord(_io__raw_record_buffer, self, self._root)
            else:
                self.record_buffer = self._io.read_bytes((self.record_length - 6))


    class FafaRecord(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.record_length = self._io.read_u4le()
            self.record_buffer = []
            for i in range(self.record_length):
                self.record_buffer.append(self._io.read_u1())



    @property
    def third_array_dimension(self):
        if hasattr(self, '_m_third_array_dimension'):
            return self._m_third_array_dimension

        _pos = self._io.pos()
        self._io.seek(182)
        self._m_third_array_dimension = self._io.read_u4le()
        self._io.seek(_pos)
        return getattr(self, '_m_third_array_dimension', None)

    @property
    def data_type_id(self):
        if hasattr(self, '_m_data_type_id'):
            return self._m_data_type_id

        _pos = self._io.pos()
        self._io.seek(190)
        self._m_data_type_id = self._io.read_u4le()
        self._io.seek(_pos)
        return getattr(self, '_m_data_type_id', None)

    @property
    def tag_name_length(self):
        if hasattr(self, '_m_tag_name_length'):
            return self._m_tag_name_length

        _pos = self._io.pos()
        self._io.seek(238)
        self._m_tag_name_length = self._io.read_u2le()
        self._io.seek(_pos)
        return getattr(self, '_m_tag_name_length', None)

    @property
    def tag_name(self):
        if hasattr(self, '_m_tag_name'):
            return self._m_tag_name

        _pos = self._io.pos()
        self._io.seek(240)
        self._m_tag_name = (self._io.read_bytes(self.tag_name_length)).decode(u"UTF-8")
        self._io.seek(_pos)
        return getattr(self, '_m_tag_name', None)


