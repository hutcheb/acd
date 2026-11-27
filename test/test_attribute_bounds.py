import struct
from types import SimpleNamespace
import pytest
from acd.generated.dat import Dat
from acd.record.attribute_bounds import complete_attributes
from acd.record.comps import CompsRecord
from acd.record.rx import RxGeneric


def rx(value):
    raw = bytearray(82)
    struct.pack_into('<H', raw, 10, 0x6A)
    raw.extend(struct.pack('<II', 0x66, len(value)) + value)
    struct.pack_into('<II', raw, 74, len(raw)-74, 1)
    return bytes(raw)


@pytest.mark.parametrize('exclude,trailer', [(False,b''),(True,b''),(False,b'JUNK')])
def test_typed_attribute_boundary_overrides_neither_payload_nor_trailer(exclude,trailer):
    payload = rx(b'12345678')
    body = bytearray(148)
    body.extend(payload)
    struct.pack_into('<I', body, 0, len(body)-(4 if exclude else 0))
    struct.pack_into('<HHII', body, 8, 0, 256, 0, 1)
    body[24:28] = b'X\0\0\0'
    body.extend(trailer)
    framed = struct.pack('<HI', 0xFAFA, 6+len(body))+body
    dat = struct.pack('<6I',0,0,23+len(framed),24,0,1)+framed
    record = Dat.from_bytes(dat).records.record[0]
    parsed = CompsRecord.parse(record)
    assert parsed[5] == payload
    assert [(a.attribute_id,a.value) for a in RxGeneric.from_bytes(parsed[5]).extended_records] == [(0x66,b'12345678')]


def test_opaque_ambiguous_bytes_do_not_satisfy_typed_contract():
    assert complete_attributes(b'ABCDEFGHWXYZ') is None


def test_incomplete_attribute_is_not_repaired_with_padding():
    raw = rx(b'12345678')[:-4]
    assert complete_attributes(raw) is None


def test_counted_end_not_outer_size_defines_payload():
    raw = rx(b'12345678')
    assert complete_attributes(raw+b'TAIL')[0] == len(raw)
    assert complete_attributes(raw[:-4]) is None
