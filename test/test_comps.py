from types import SimpleNamespace

import pytest

from acd.record.comps import CompsRecord


def _comps_record(identifier, legacy):
    payload = b"\x11\x22\x33\x44\x55\x66\x77\x88"
    object_offset = 0x0C if legacy else 0x10
    name_offset = object_offset + 8

    if identifier == 0xFAFA:
        payload_start = 0x90 if legacy else 0x94
        physical_length = payload_start + len(payload)
        record_length = physical_length - 4 if legacy else physical_length
        raw = bytearray(physical_length)
        raw[0:4] = record_length.to_bytes(4, "little")
        len_record = len(raw) + 6
    else:
        payload_start = 0x97 if legacy else 0x9B
        raw = bytearray(payload_start + len(payload) + 2)
        len_record = len(raw) + 6

    seq_offset = 8 if identifier == 0xFAFA else 4
    raw[seq_offset : seq_offset + 2] = (7).to_bytes(2, "little")
    raw[10:12] = (256).to_bytes(2, "little")
    raw[object_offset : object_offset + 4] = (0x12345678).to_bytes(4, "little")
    raw[object_offset + 4 : object_offset + 8] = (0).to_bytes(4, "little")
    name = ("LegacyController" if legacy else "ModernController").encode(
        "utf-16-le"
    ) + b"\0\0"
    raw[name_offset : name_offset + len(name)] = name
    raw[payload_start : payload_start + len(payload)] = payload

    return SimpleNamespace(
        identifier=identifier,
        len_record=len_record,
        record=SimpleNamespace(record_buffer=bytes(raw)),
    )


@pytest.mark.parametrize("identifier", [0xFAFA, 0xFDFD])
@pytest.mark.parametrize("legacy", [False, True])
def test_parse_comps_layout(identifier, legacy):
    result = CompsRecord.parse(_comps_record(identifier, legacy))

    assert result == (
        0x12345678,
        0,
        "LegacyController" if legacy else "ModernController",
        7,
        256,
        b"\x11\x22\x33\x44\x55\x66\x77\x88",
    )


def test_legacy_region_map_ignores_unrelated_outer_trailer():
    record = _comps_record(0xFAFA, True)
    raw = bytearray(record.record.record_buffer)
    name = "Region Map".encode("utf-16-le") + b"\0\0"
    raw[0x14 : 0x14 + len(name)] = name
    raw.extend(b"unrelated database bytes")
    record.record.record_buffer = bytes(raw)

    result = CompsRecord.parse(record)

    assert result[5] == b"\x11\x22\x33\x44\x55\x66\x77\x88"
