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
        self.parent_id = self._io.read_u4le()
        self.unique_tag_identifier = self._io.read_u4le()
        self.record_format_version = self._io.read_u2le()
        self.comment_id = self._io.read_u4le()
        _on = self.record_format_version
        if _on == 0:
            self.body = RxTag.V0(self._io, self, self._root)
        elif _on == 60:
            self.body = RxTag.V60(self._io, self, self._root)
        elif _on == 63:
            self.body = RxTag.V63(self._io, self, self._root)
        else:
            self.body = RxTag.VUnknown(self._io, self, self._root)

    class V63(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            pass

        @property
        def cip_data_type(self):
            if hasattr(self, '_m_cip_data_type'):
                return self._m_cip_data_type

            _pos = self._io.pos()
            self._io.seek(66)
            self._m_cip_data_type = self._io.read_u2le()
            self._io.seek(_pos)
            return getattr(self, '_m_cip_data_type', None)

        @property
        def tag_name_length(self):
            if hasattr(self, '_m_tag_name_length'):
                return self._m_tag_name_length

            _pos = self._io.pos()
            self._io.seek((78 + (len(self.records) * 4)))
            self._m_tag_name_length = self._io.read_u2le()
            self._io.seek(_pos)
            return getattr(self, '_m_tag_name_length', None)

        @property
        def device_map_instance(self):
            if hasattr(self, '_m_device_map_instance'):
                return self._m_device_map_instance

            _pos = self._io.pos()
            self._io.seek(372)
            self._m_device_map_instance = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_device_map_instance', None)

        @property
        def data_type(self):
            if hasattr(self, '_m_data_type'):
                return self._m_data_type

            _pos = self._io.pos()
            self._io.seek(42)
            self._m_data_type = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_data_type', None)

        @property
        def data_instance(self):
            if hasattr(self, '_m_data_instance'):
                return self._m_data_instance

            _pos = self._io.pos()
            self._io.seek(358)
            self._m_data_instance = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_data_instance', None)

        @property
        def dimension_2(self):
            if hasattr(self, '_m_dimension_2'):
                return self._m_dimension_2

            _pos = self._io.pos()
            self._io.seek(30)
            self._m_dimension_2 = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_dimension_2', None)

        @property
        def dimension_3(self):
            if hasattr(self, '_m_dimension_3'):
                return self._m_dimension_3

            _pos = self._io.pos()
            self._io.seek(34)
            self._m_dimension_3 = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_dimension_3', None)

        @property
        def valid(self):
            if hasattr(self, '_m_valid'):
                return self._m_valid

            self._m_valid = True
            return getattr(self, '_m_valid', None)

        @property
        def sub_record_length(self):
            if hasattr(self, '_m_sub_record_length'):
                return self._m_sub_record_length

            _pos = self._io.pos()
            self._io.seek((78 + (len(self.records) * 4)))
            self._m_sub_record_length = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_sub_record_length', None)

        @property
        def logical_path(self):
            if hasattr(self, '_m_logical_path'):
                return self._m_logical_path

            _pos = self._io.pos()
            self._io.seek(666)
            self._m_logical_path = RxTag.LogicalPath(self._io, self, self._root)
            self._io.seek(_pos)
            return getattr(self, '_m_logical_path', None)

        @property
        def name(self):
            if hasattr(self, '_m_name'):
                return self._m_name

            _pos = self._io.pos()
            self._io.seek(((78 + (len(self.records) * 4)) + 2))
            self._m_name = (self._io.read_bytes(self.tag_name_length)).decode(u"UTF-8")
            self._io.seek(_pos)
            return getattr(self, '_m_name', None)

        @property
        def dimension_1(self):
            if hasattr(self, '_m_dimension_1'):
                return self._m_dimension_1

            _pos = self._io.pos()
            self._io.seek(26)
            self._m_dimension_1 = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_dimension_1', None)

        @property
        def records(self):
            if hasattr(self, '_m_records'):
                return self._m_records

            _pos = self._io.pos()
            self._io.seek(78)
            self._m_records = []
            i = 0
            while True:
                _ = self._io.read_u4le()
                self._m_records.append(_)
                if _ == 590:
                    break
                i += 1
            self._io.seek(_pos)
            return getattr(self, '_m_records', None)

        @property
        def data_table_instance(self):
            if hasattr(self, '_m_data_table_instance'):
                return self._m_data_table_instance

            _pos = self._io.pos()
            self._io.seek(50)
            self._m_data_table_instance = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_data_table_instance', None)


    class V60(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            pass

        @property
        def cip_data_type(self):
            if hasattr(self, '_m_cip_data_type'):
                return self._m_cip_data_type

            _pos = self._io.pos()
            self._io.seek(66)
            self._m_cip_data_type = self._io.read_u2le()
            self._io.seek(_pos)
            return getattr(self, '_m_cip_data_type', None)

        @property
        def tag_name_length(self):
            if hasattr(self, '_m_tag_name_length'):
                return self._m_tag_name_length

            _pos = self._io.pos()
            self._io.seek(90)
            self._m_tag_name_length = self._io.read_u2le()
            self._io.seek(_pos)
            return getattr(self, '_m_tag_name_length', None)

        @property
        def data_type(self):
            if hasattr(self, '_m_data_type'):
                return self._m_data_type

            _pos = self._io.pos()
            self._io.seek(42)
            self._m_data_type = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_data_type', None)

        @property
        def dimension_2(self):
            if hasattr(self, '_m_dimension_2'):
                return self._m_dimension_2

            _pos = self._io.pos()
            self._io.seek(30)
            self._m_dimension_2 = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_dimension_2', None)

        @property
        def dimension_3(self):
            if hasattr(self, '_m_dimension_3'):
                return self._m_dimension_3

            _pos = self._io.pos()
            self._io.seek(34)
            self._m_dimension_3 = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_dimension_3', None)

        @property
        def valid(self):
            if hasattr(self, '_m_valid'):
                return self._m_valid

            self._m_valid = True
            return getattr(self, '_m_valid', None)

        @property
        def logical_path(self):
            if hasattr(self, '_m_logical_path'):
                return self._m_logical_path

            _pos = self._io.pos()
            self._io.seek(666)
            self._m_logical_path = RxTag.LogicalPath(self._io, self, self._root)
            self._io.seek(_pos)
            return getattr(self, '_m_logical_path', None)

        @property
        def name(self):
            if hasattr(self, '_m_name'):
                return self._m_name

            _pos = self._io.pos()
            self._io.seek(92)
            self._m_name = (self._io.read_bytes(self.tag_name_length)).decode(u"UTF-8")
            self._io.seek(_pos)
            return getattr(self, '_m_name', None)

        @property
        def dimension_1(self):
            if hasattr(self, '_m_dimension_1'):
                return self._m_dimension_1

            _pos = self._io.pos()
            self._io.seek(26)
            self._m_dimension_1 = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_dimension_1', None)

        @property
        def data_table_instance(self):
            if hasattr(self, '_m_data_table_instance'):
                return self._m_data_table_instance

            _pos = self._io.pos()
            self._io.seek(50)
            self._m_data_table_instance = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_data_table_instance', None)


    class LogicalPath(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.position_0 = self._io.read_u4le()
            self.position_1 = self._io.read_u4le()
            self.position_2 = self._io.read_u4le()
            self.position_3 = self._io.read_u4le()
            self.position_4 = self._io.read_u4le()


    class V0(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            pass

        @property
        def valid(self):
            if hasattr(self, '_m_valid'):
                return self._m_valid

            self._m_valid = False
            return getattr(self, '_m_valid', None)


    class VUnknown(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            pass

        @property
        def valid(self):
            if hasattr(self, '_m_valid'):
                return self._m_valid

            self._m_valid = False
            return getattr(self, '_m_valid', None)


    class V63Records(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.unknown_0 = self._io.read_u4le()
            self.unknown_1 = self._io.read_u4le()
            self.unknown_2 = self._io.read_u4le()



