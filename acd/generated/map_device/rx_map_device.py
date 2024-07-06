# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 9):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class RxMapDevice(KaitaiStruct):
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
            self.body = RxMapDevice.V0(self._io, self, self._root)
        elif _on == 162:
            self.body = RxMapDevice.V162(self._io, self, self._root)
        elif _on == 173:
            self.body = RxMapDevice.V173(self._io, self, self._root)
        else:
            self.body = RxMapDevice.VUnknown(self._io, self, self._root)

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


    class V162(KaitaiStruct):
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
            self._io.seek(126)
            self._m_module_id = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_module_id', None)

        @property
        def valid(self):
            if hasattr(self, '_m_valid'):
                return self._m_valid

            self._m_valid = True
            return getattr(self, '_m_valid', None)

        @property
        def record_length(self):
            if hasattr(self, '_m_record_length'):
                return self._m_record_length

            _pos = self._io.pos()
            self._io.seek(74)
            self._m_record_length = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_record_length', None)

        @property
        def product_type(self):
            if hasattr(self, '_m_product_type'):
                return self._m_product_type

            _pos = self._io.pos()
            self._io.seek(94)
            self._m_product_type = self._io.read_u2le()
            self._io.seek(_pos)
            return getattr(self, '_m_product_type', None)

        @property
        def vendor_id(self):
            if hasattr(self, '_m_vendor_id'):
                return self._m_vendor_id

            _pos = self._io.pos()
            self._io.seek(92)
            self._m_vendor_id = self._io.read_u2le()
            self._io.seek(_pos)
            return getattr(self, '_m_vendor_id', None)

        @property
        def slot_no(self):
            if hasattr(self, '_m_slot_no'):
                return self._m_slot_no

            _pos = self._io.pos()
            self._io.seek(122)
            self._m_slot_no = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_slot_no', None)

        @property
        def product_code(self):
            if hasattr(self, '_m_product_code'):
                return self._m_product_code

            _pos = self._io.pos()
            self._io.seek(96)
            self._m_product_code = self._io.read_u2le()
            self._io.seek(_pos)
            return getattr(self, '_m_product_code', None)

        @property
        def parent_module(self):
            if hasattr(self, '_m_parent_module'):
                return self._m_parent_module

            _pos = self._io.pos()
            self._io.seek(112)
            self._m_parent_module = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_parent_module', None)


    class V173(KaitaiStruct):
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
            self._io.seek((((80 + 4) + (self.record_count * 12)) + 38))
            self._m_module_id = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_module_id', None)

        @property
        def valid(self):
            if hasattr(self, '_m_valid'):
                return self._m_valid

            self._m_valid = True
            return getattr(self, '_m_valid', None)

        @property
        def record_count(self):
            if hasattr(self, '_m_record_count'):
                return self._m_record_count

            _pos = self._io.pos()
            self._io.seek(78)
            self._m_record_count = self._io.read_u2le()
            self._io.seek(_pos)
            return getattr(self, '_m_record_count', None)

        @property
        def record_length(self):
            if hasattr(self, '_m_record_length'):
                return self._m_record_length

            _pos = self._io.pos()
            self._io.seek(74)
            self._m_record_length = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_record_length', None)

        @property
        def product_type(self):
            if hasattr(self, '_m_product_type'):
                return self._m_product_type

            _pos = self._io.pos()
            self._io.seek(((80 + 2) + (self.record_count * 12)))
            self._m_product_type = self._io.read_u2le()
            self._io.seek(_pos)
            return getattr(self, '_m_product_type', None)

        @property
        def vendor_id(self):
            if hasattr(self, '_m_vendor_id'):
                return self._m_vendor_id

            _pos = self._io.pos()
            self._io.seek((80 + (self.record_count * 12)))
            self._m_vendor_id = self._io.read_u2le()
            self._io.seek(_pos)
            return getattr(self, '_m_vendor_id', None)

        @property
        def slot_no(self):
            if hasattr(self, '_m_slot_no'):
                return self._m_slot_no

            _pos = self._io.pos()
            self._io.seek((((80 + 4) + (self.record_count * 12)) + 22))
            self._m_slot_no = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_slot_no', None)

        @property
        def product_code(self):
            if hasattr(self, '_m_product_code'):
                return self._m_product_code

            _pos = self._io.pos()
            self._io.seek(((80 + 4) + (self.record_count * 12)))
            self._m_product_code = self._io.read_u2le()
            self._io.seek(_pos)
            return getattr(self, '_m_product_code', None)

        @property
        def records(self):
            if hasattr(self, '_m_records'):
                return self._m_records

            _pos = self._io.pos()
            self._io.seek(80)
            self._m_records = []
            for i in range(self.record_count):
                self._m_records.append(self._io.read_bytes(12))

            self._io.seek(_pos)
            return getattr(self, '_m_records', None)

        @property
        def parent_module(self):
            if hasattr(self, '_m_parent_module'):
                return self._m_parent_module

            _pos = self._io.pos()
            self._io.seek(((80 + (self.record_count * 12)) + 20))
            self._m_parent_module = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_parent_module', None)



