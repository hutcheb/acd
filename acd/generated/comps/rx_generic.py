# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 9):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class RxGeneric(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.parent_id = self._io.read_u4le()
        self.unique_tag_identifier = self._io.read_u4le()
        self.record_format_version = self._io.read_u2le()
        self.cip_type = self._io.read_u2le()
        self.comment_id = self._io.read_u2le()
        _on = self.cip_type
        if _on == 107:
            self._raw_main_record = self._io.read_bytes(60)
            _io__raw_main_record = KaitaiStream(BytesIO(self._raw_main_record))
            self.main_record = RxGeneric.RxTag(_io__raw_main_record, self, self._root)
        else:
            self._raw_main_record = self._io.read_bytes(60)
            _io__raw_main_record = KaitaiStream(BytesIO(self._raw_main_record))
            self.main_record = RxGeneric.Unknown(_io__raw_main_record, self, self._root)
        self.len_record = self._io.read_u4le()
        self.count_record = self._io.read_u4le()
        self.extended_records = []
        for i in range((self.count_record - 1)):
            self.extended_records.append(RxGeneric.AttributeRecord(self._io, self, self._root))

        self.last_extended_record = RxGeneric.LastAttributeRecord(self._io, self, self._root)

    class Unknown(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.body = self._io.read_bytes(60)


    class LastAttributeRecord(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.attribute_id = self._io.read_u4le()
            self.record_length = self._io.read_u4le()
            self.value = self._io.read_bytes((self.record_length - 4))


    class RxMapDevice(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            pass

        @property
        def module_id(self):
            if hasattr(self, '_m_module_id'):
                return self._m_module_id

            _pos = self._io.pos()
            self._io.seek(36)
            self._m_module_id = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_module_id', None)

        @property
        def product_type(self):
            if hasattr(self, '_m_product_type'):
                return self._m_product_type

            _pos = self._io.pos()
            self._io.seek(4)
            self._m_product_type = self._io.read_u2le()
            self._io.seek(_pos)
            return getattr(self, '_m_product_type', None)

        @property
        def vendor_id(self):
            if hasattr(self, '_m_vendor_id'):
                return self._m_vendor_id

            _pos = self._io.pos()
            self._io.seek(2)
            self._m_vendor_id = self._io.read_u2le()
            self._io.seek(_pos)
            return getattr(self, '_m_vendor_id', None)

        @property
        def slot_no(self):
            if hasattr(self, '_m_slot_no'):
                return self._m_slot_no

            _pos = self._io.pos()
            self._io.seek(32)
            self._m_slot_no = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_slot_no', None)

        @property
        def product_code(self):
            if hasattr(self, '_m_product_code'):
                return self._m_product_code

            _pos = self._io.pos()
            self._io.seek(6)
            self._m_product_code = self._io.read_u2le()
            self._io.seek(_pos)
            return getattr(self, '_m_product_code', None)

        @property
        def parent_module(self):
            if hasattr(self, '_m_parent_module'):
                return self._m_parent_module

            _pos = self._io.pos()
            self._io.seek(22)
            self._m_parent_module = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_parent_module', None)


    class RxTag(KaitaiStruct):
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
            self._io.seek(52)
            self._m_cip_data_type = self._io.read_u2le()
            self._io.seek(_pos)
            return getattr(self, '_m_cip_data_type', None)

        @property
        def data_type(self):
            if hasattr(self, '_m_data_type'):
                return self._m_data_type

            _pos = self._io.pos()
            self._io.seek(28)
            self._m_data_type = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_data_type', None)

        @property
        def dimension_2(self):
            if hasattr(self, '_m_dimension_2'):
                return self._m_dimension_2

            _pos = self._io.pos()
            self._io.seek(16)
            self._m_dimension_2 = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_dimension_2', None)

        @property
        def dimension_3(self):
            if hasattr(self, '_m_dimension_3'):
                return self._m_dimension_3

            _pos = self._io.pos()
            self._io.seek(20)
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
        def dimension_1(self):
            if hasattr(self, '_m_dimension_1'):
                return self._m_dimension_1

            _pos = self._io.pos()
            self._io.seek(12)
            self._m_dimension_1 = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_dimension_1', None)

        @property
        def data_table_instance(self):
            if hasattr(self, '_m_data_table_instance'):
                return self._m_data_table_instance

            _pos = self._io.pos()
            self._io.seek(36)
            self._m_data_table_instance = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_data_table_instance', None)


    class AttributeRecord(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.attribute_id = self._io.read_u4le()
            self.record_length = self._io.read_u4le()
            self.value = self._io.read_bytes(self.record_length)



