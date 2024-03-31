# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 9):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class RxTag(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.header = RxTag.Header(self._io, self, self._root)
        self.parent_id = self._io.read_u4le()
        self.unique_tag_identifier = self._io.read_u4le()

    class Header(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.length = self._io.read_u4le()
            self.blank_1 = self._io.read_u4le()
            self.seq_number = self._io.read_u2le()
            self.record_type = self._io.read_u2le()
            self.blank_2 = self._io.read_u4le()
            self.object_id = self._io.read_u4le()
            self.parent_id = self._io.read_u4le()
            self.name = (self._io.read_bytes(124)).decode(u"UTF-16")


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
    def data_type_id(self):
        if hasattr(self, '_m_data_type_id'):
            return self._m_data_type_id

        _pos = self._io.pos()
        self._io.seek(190)
        self._m_data_type_id = self._io.read_u4le()
        self._io.seek(_pos)
        return getattr(self, '_m_data_type_id', None)

    @property
    def tag_name(self):
        if hasattr(self, '_m_tag_name'):
            return self._m_tag_name

        _pos = self._io.pos()
        self._io.seek(240)
        self._m_tag_name = (self._io.read_bytes(self.tag_name_length)).decode(u"UTF-8")
        self._io.seek(_pos)
        return getattr(self, '_m_tag_name', None)

    @property
    def second_array_dimension(self):
        if hasattr(self, '_m_second_array_dimension'):
            return self._m_second_array_dimension

        _pos = self._io.pos()
        self._io.seek(178)
        self._m_second_array_dimension = self._io.read_u4le()
        self._io.seek(_pos)
        return getattr(self, '_m_second_array_dimension', None)

    @property
    def first_array_dimension(self):
        if hasattr(self, '_m_first_array_dimension'):
            return self._m_first_array_dimension

        _pos = self._io.pos()
        self._io.seek(174)
        self._m_first_array_dimension = self._io.read_u4le()
        self._io.seek(_pos)
        return getattr(self, '_m_first_array_dimension', None)

    @property
    def third_array_dimension(self):
        if hasattr(self, '_m_third_array_dimension'):
            return self._m_third_array_dimension

        _pos = self._io.pos()
        self._io.seek(182)
        self._m_third_array_dimension = self._io.read_u4le()
        self._io.seek(_pos)
        return getattr(self, '_m_third_array_dimension', None)


