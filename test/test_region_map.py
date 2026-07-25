import pytest

from acd.l5x.export_l5x import ExportL5x


def test_parse_empty_modern_region_map():
    assert ExportL5x._parse_region_map(bytes(0x4A)) == []


@pytest.mark.parametrize("legacy", [False, True])
def test_parse_region_map_layout(legacy):
    entries = [
        (0x11111111, 1, 2, 3),
        (0x22222222, 4, 5, 6),
    ]

    if legacy:
        identifier_offset = 0x1C
        record = bytearray(identifier_offset + len(entries) * 16)
        record[0x18:0x1C] = (len(record) - 0x1C).to_bytes(4, "little")
    else:
        identifier_offset = 0x4E
        region_length = len(entries) * 16 + 4
        record = bytearray(identifier_offset + region_length - 4)
        record[0x4A:0x4E] = region_length.to_bytes(4, "little")

    expected = []
    for object_id, parent_id, unknown, sequence in entries:
        raw_entry = (
            parent_id.to_bytes(4, "little")
            + unknown.to_bytes(4, "little")
            + sequence.to_bytes(4, "little")
            + object_id.to_bytes(4, "little")
        )
        record[identifier_offset : identifier_offset + 16] = raw_entry
        expected.append((object_id, parent_id, unknown, sequence, raw_entry))
        identifier_offset += 16

    assert ExportL5x._parse_region_map(bytes(record)) == expected


def test_parse_region_map_rejects_truncated_record():
    record = bytearray(0x1C + 16)
    record[0x18:0x1C] = (32).to_bytes(4, "little")

    with pytest.raises(ValueError, match="Invalid Region Map length"):
        ExportL5x._parse_region_map(bytes(record))


def test_modern_region_map_wins_legacy_length_collision():
    record = bytearray(0x4E + 16)
    record[0x18:0x1C] = (len(record) - 0x1C).to_bytes(4, "little")
    record[0x4A:0x4E] = (20).to_bytes(4, "little")
    entry = (1, 2, 3, 4)
    record[0x4E:] = b"".join(value.to_bytes(4, "little") for value in entry)

    assert ExportL5x._parse_region_map(bytes(record)) == [
        (4, 1, 2, 3, bytes(record[0x4E:]))
    ]
