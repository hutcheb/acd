import struct
from types import SimpleNamespace

from acd.record.sbregion import SbRegionRecord


def _sbregion_record(identifier, language_type, payload):
    language = language_type.encode("utf-8").ljust(41, b"\x00")
    header = struct.pack("<HI", 0, identifier) + language
    body = header + struct.pack("<I", len(payload)) + payload
    buffer = struct.pack("<I", len(body)) + body
    return SimpleNamespace(identifier=64250, record=SimpleNamespace(record_buffer=buffer))


def test_parse_rung_text_resolves_tag_references():
    text = "XIC(@0000002A@)OTE(Out);\x00".encode("utf-16-le")
    record = _sbregion_record(7, "Rung NT", text)

    assert SbRegionRecord.parse(record, {0x2A: "Start"}) == (7, "XIC(Start)OTE(Out);", "")


def test_parse_skips_record_that_is_not_utf16_text():
    # Odd length and a lone low surrogate: what an encrypted (source
    # protected) routine looks like to a UTF-16 decoder.
    record = _sbregion_record(8, "REGION NT", b"\x00\xdc\x41")

    assert SbRegionRecord.parse(record, {}) is None


def test_parse_ignores_other_language_types():
    record = _sbregion_record(9, "REGION AST", b"\x00\xdc\x41")

    assert SbRegionRecord.parse(record, {}) is None
