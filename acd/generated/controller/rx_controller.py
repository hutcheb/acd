# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 9):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class RxController(KaitaiStruct):
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
        if _on == 95:
            self.body = RxController.V95(self._io, self, self._root)
        elif _on == 103:
            self.body = RxController.V103(self._io, self, self._root)
        else:
            self.body = RxController.VUnknown(self._io, self, self._root)

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


    class V95(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            pass

        @property
        def len_most_recent(self):
            if hasattr(self, '_m_len_most_recent'):
                return self._m_len_most_recent

            _pos = self._io.pos()
            self._io.seek(363)
            self._m_len_most_recent = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_len_most_recent', None)

        @property
        def record(self):
            if hasattr(self, '_m_record'):
                return self._m_record

            _pos = self._io.pos()
            self._io.seek(74)
            self._m_record = self._io.read_bytes(self.len_record)
            self._io.seek(_pos)
            return getattr(self, '_m_record', None)

        @property
        def len_current_active(self):
            if hasattr(self, '_m_len_current_active'):
                return self._m_len_current_active

            _pos = self._io.pos()
            self._io.seek(327)
            self._m_len_current_active = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_len_current_active', None)

        @property
        def most_recent(self):
            if hasattr(self, '_m_most_recent'):
                return self._m_most_recent

            _pos = self._io.pos()
            self._io.seek(367)
            self._m_most_recent = (self._io.read_bytes(self.len_most_recent)).decode(u"utf-16")
            self._io.seek(_pos)
            return getattr(self, '_m_most_recent', None)

        @property
        def serial_number(self):
            if hasattr(self, '_m_serial_number'):
                return self._m_serial_number

            _pos = self._io.pos()
            self._io.seek(459)
            self._m_serial_number = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_serial_number', None)

        @property
        def valid(self):
            if hasattr(self, '_m_valid'):
                return self._m_valid

            self._m_valid = True
            return getattr(self, '_m_valid', None)

        @property
        def len_record(self):
            if hasattr(self, '_m_len_record'):
                return self._m_len_record

            _pos = self._io.pos()
            self._io.seek(74)
            self._m_len_record = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_len_record', None)

        @property
        def current_acive(self):
            if hasattr(self, '_m_current_acive'):
                return self._m_current_acive

            _pos = self._io.pos()
            self._io.seek(331)
            self._m_current_acive = (self._io.read_bytes(self.len_current_active)).decode(u"utf-16")
            self._io.seek(_pos)
            return getattr(self, '_m_current_acive', None)


    class V103(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            pass

        @property
        def len_most_recent(self):
            if hasattr(self, '_m_len_most_recent'):
                return self._m_len_most_recent

            _pos = self._io.pos()
            self._io.seek(232)
            self._m_len_most_recent = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_len_most_recent', None)

        @property
        def record(self):
            if hasattr(self, '_m_record'):
                return self._m_record

            _pos = self._io.pos()
            self._io.seek(74)
            self._m_record = self._io.read_bytes(self.len_record)
            self._io.seek(_pos)
            return getattr(self, '_m_record', None)

        @property
        def len_current_active(self):
            if hasattr(self, '_m_len_current_active'):
                return self._m_len_current_active

            _pos = self._io.pos()
            self._io.seek(196)
            self._m_len_current_active = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_len_current_active', None)

        @property
        def most_recent(self):
            if hasattr(self, '_m_most_recent'):
                return self._m_most_recent

            _pos = self._io.pos()
            self._io.seek(236)
            self._m_most_recent = (self._io.read_bytes(self.len_most_recent)).decode(u"utf-16")
            self._io.seek(_pos)
            return getattr(self, '_m_most_recent', None)

        @property
        def serial_number(self):
            if hasattr(self, '_m_serial_number'):
                return self._m_serial_number

            _pos = self._io.pos()
            self._io.seek(328)
            self._m_serial_number = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_serial_number', None)

        @property
        def valid(self):
            if hasattr(self, '_m_valid'):
                return self._m_valid

            self._m_valid = True
            return getattr(self, '_m_valid', None)

        @property
        def len_record(self):
            if hasattr(self, '_m_len_record'):
                return self._m_len_record

            _pos = self._io.pos()
            self._io.seek(74)
            self._m_len_record = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_len_record', None)

        @property
        def path(self):
            if hasattr(self, '_m_path'):
                return self._m_path

            _pos = self._io.pos()
            self._io.seek(388)
            self._m_path = (self._io.read_bytes(self.len_path)).decode(u"utf-16")
            self._io.seek(_pos)
            return getattr(self, '_m_path', None)

        @property
        def len_path(self):
            if hasattr(self, '_m_len_path'):
                return self._m_len_path

            _pos = self._io.pos()
            self._io.seek(384)
            self._m_len_path = self._io.read_u4le()
            self._io.seek(_pos)
            return getattr(self, '_m_len_path', None)

        @property
        def current_acive(self):
            if hasattr(self, '_m_current_acive'):
                return self._m_current_acive

            _pos = self._io.pos()
            self._io.seek(200)
            self._m_current_acive = (self._io.read_bytes(self.len_current_active)).decode(u"utf-16")
            self._io.seek(_pos)
            return getattr(self, '_m_current_acive', None)



