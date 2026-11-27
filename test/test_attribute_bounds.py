import struct
from types import SimpleNamespace
import pytest
from acd.generated.dat import Dat
from acd.record.attribute_bounds import complete_attributes
from acd.record.comps import CompsRecord
from acd.record.rx import RxGeneric
from acd.record.attribute_bounds import attribute_layout


@pytest.fixture(autouse=True)
def explicit_counted_input_contract():
    with attribute_layout('complete-counted'):
        yield


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


def test_aoi_declaration_final_alias_attribute_is_retained():
    raw = bytearray(rx('@12345678@.0'.encode('utf-16-le')))
    struct.pack_into('<H', raw, 10, 0x338)
    struct.pack_into('<I', raw, 82, 0x65)
    parsed = RxGeneric.from_bytes(raw)
    assert [(a.attribute_id, a.value) for a in parsed.extended_records] == [(0x65, '@12345678@.0'.encode('utf-16-le'))]


def test_arbitrary_trailing_data_is_outside_the_supported_contract():
    assert complete_attributes(rx(b'12345678') + b'TRAILER!') is None


def test_inflated_final_attribute_and_outer_trailer_cannot_be_autodetected():
    payload = bytearray(rx(b'12345678')[:-4])
    struct.pack_into('<I', payload, 74, len(payload)-74)
    body = bytearray(148) + payload
    struct.pack_into('<I', body, 0, len(body))
    struct.pack_into('<HHII', body, 8, 0, 256, 0, 1)
    body[24:28] = b'X\0\0\0'
    body.extend(b'JUNK')
    framed = struct.pack('<HI', 0xfafa, len(body)+6) + body
    dat = struct.pack('<6I',0,0,23+len(framed),24,0,1) + framed
    record = Dat.from_bytes(dat).records.record[0]
    with attribute_layout('compat'):
        assert CompsRecord.parse(record)[5] == payload
    # The identical bytes admit another interpretation. Only a caller that
    # independently established complete counted attributes may select it.
    with attribute_layout('complete-counted'):
        assert CompsRecord.parse(record)[5] == payload + b'JUNK'


@pytest.mark.parametrize('exclude,trailer', [(False,b''), (True,b''), (False,b'JUNK')])
def test_normal_converter_with_typed_dat_boundary(tmp_path, exclude, trailer):
    import gzip
    from pathlib import Path
    import xml.etree.ElementTree as ET
    from acd.api import load_acd, ConvertAcdToL5x
    from acd.l5x.export_l5x import ExportL5x
    from acd.zip.write_acd import build_acd_bytes

    source = load_acd(Path(__file__).resolve().parents[1] / 'resources' / 'ACDTestsWithAOI.ACD')
    files = dict(source._raw_files)
    compressed = files['Comps.Dat'].startswith(b'\x1f\x8b')
    dat = gzip.decompress(files['Comps.Dat']) if compressed else files['Comps.Dat']
    dat = bytearray(dat[:struct.unpack_from('<I', dat, 8)[0] + 1])
    payload = rx(b'ABCDWXYZ')
    body = bytearray(148) + payload
    struct.pack_into('<I', body, 0, len(body) - (4 if exclude else 0))
    struct.pack_into('<HHIII', body, 8, 0, 256, 0, 0xc0debeef, 0xc0debe00)
    name = 'SyntheticBuffer\0'.encode('utf-16-le')
    body[24:24+len(name)] = name
    body.extend(trailer)
    dat.extend(struct.pack('<HI', 0xfafa, 6 + len(body)) + body)
    struct.pack_into('<I', dat, 8, len(dat) - 1)
    files['Comps.Dat'] = gzip.compress(bytes(dat)) if compressed else bytes(dat)
    acd = tmp_path / 'synthetic.ACD'
    acd.write_bytes(build_acd_bytes(files, source._file_order, source._footer_unknown))
    export = ExportL5x(acd, str(tmp_path / 'database'))
    try:
        recovered = export._cur.execute('SELECT record FROM comps WHERE object_id=?', (0xc0debeef,)).fetchone()[0]
        assert recovered == payload
        assert RxGeneric.from_bytes(recovered).extended_records[0].value == b'ABCDWXYZ'
    finally:
        export._db.close()
    destination = tmp_path / 'output.L5X'
    ConvertAcdToL5x(acd, destination).extract()
    assert ET.parse(destination).getroot().find('Controller') is not None
