import sqlite3
import struct

import pytest

from acd.l5x.elements import TagBuilder, TaskBuilder, _program_schedule_id
from acd.record.rx import LegacyRxGeneric, RxGeneric


def _metadata(name, runtime_type=0xC4, dimensions=(0, 0, 0), schedule_id=None):
    value = bytearray(544)
    encoded_name = name.encode("utf-8")
    struct.pack_into("<H", value, 0, len(encoded_name))
    value[2 : 2 + len(encoded_name)] = encoded_name
    struct.pack_into("<H", value, 0x100, runtime_type)
    struct.pack_into("<I", value, 0x102, 123)
    value[0x20F] = 4 << 4
    struct.pack_into("<III", value, 0x212, *dimensions)
    struct.pack_into("<H", value, 0x21E, 0)
    if schedule_id is not None:
        struct.pack_into("<I", value, 267, schedule_id)
    return bytes(value)


def _legacy_rx(
    *,
    cip_type=0x6B,
    data_instance_id=0,
    object_id=1,
    runtime_type=0,
    comment_id=0,
    attributes=(),
):
    raw = bytearray(32)
    struct.pack_into("<II", raw, 0, data_instance_id, 0x12345678)
    struct.pack_into("<HH", raw, 8, cip_type, comment_id)
    struct.pack_into("<I", raw, 16, runtime_type)
    struct.pack_into("<I", raw, 20, object_id)
    struct.pack_into("<I", raw, 28, len(attributes))
    for attribute_id, value in attributes:
        raw.extend(struct.pack("<II", attribute_id, len(value)))
        raw.extend(value)
    struct.pack_into("<I", raw, 24, len(raw) - 28)
    return bytes(raw)


def _database():
    database = sqlite3.connect(":memory:")
    cursor = database.cursor()
    cursor.execute(
        "CREATE TABLE comps(object_id int, parent_id int, comp_name text, "
        "seq_number int, record_type int, record BLOB NOT NULL)"
    )
    cursor.execute(
        "CREATE TABLE comments(seq_number int, sub_record_length int, "
        "object_id int, record_string text, record_type int, parent int, "
        "tag_reference text, rung_content int, member_ref int)"
    )
    return database, cursor


def _insert(cursor, object_id, name, record, parent_id=0):
    cursor.execute(
        "INSERT INTO comps VALUES (?, ?, ?, ?, ?, ?)",
        (object_id, parent_id, name, 0, 256, record),
    )


def test_parse_legacy_rx_generic():
    attributes = [
        (0x65, b"\x01\x02\x03\x04"),
        (0x66, b"\x05\x06\x07\x08"),
    ]
    raw = _legacy_rx(
        data_instance_id=0xFFFFFFFF,
        object_id=0x87654321,
        runtime_type=0xC4,
        comment_id=3,
        attributes=attributes,
    )

    result = RxGeneric.from_bytes(raw)

    assert isinstance(result, LegacyRxGeneric)
    assert result.data_instance_id == 0xFFFFFFFF
    assert result.unique_tag_identifier == 0x12345678
    assert result.record_format_version == 0
    assert result.cip_type == 0x6B
    assert result.comment_id == 3
    assert result.object_id == 0x87654321
    assert result.main_record.data_type == 0xC4
    assert result.record_buffer == raw[14:74]
    assert [
        (attribute.attribute_id, attribute.value)
        for attribute in result.extended_records
    ] == attributes


def test_modern_rx_layout_wins_legacy_length_collision():
    raw = bytearray(82)
    struct.pack_into("<H", raw, 10, 0x6B)
    struct.pack_into("<I", raw, 24, len(raw) - 24)
    struct.pack_into("<I", raw, 74, len(raw) - 74)
    struct.pack_into("<I", raw, 78, 1)

    result = RxGeneric.from_bytes(bytes(raw))

    assert not isinstance(result, LegacyRxGeneric)
    assert result.cip_type == 0x6B


def test_legacy_rx_accepts_short_final_attribute():
    raw = bytearray(
        _legacy_rx(attributes=[(0x01, b"\x01\x02\x03\x04")])
    )
    struct.pack_into("<I", raw, 36, 8)
    struct.pack_into("<I", raw, 24, len(raw) - 24)

    result = RxGeneric.from_bytes(bytes(raw))

    assert result.extended_records[0].len_value == 8
    assert result.extended_records[0].value == b"\x01\x02\x03\x04"


@pytest.mark.parametrize(
    "type_name,runtime_type,dimensions,expected_dimensions",
    [
        ("DINT", 0xC4, (0, 0, 0), None),
        ("REAL", 0x20CA, (10, 0, 0), "10"),
        ("strItemInfo", 0xA1E7, (200, 0, 0), "200"),
        ("BOOL", 0x20D3, (1, 0, 0), "32"),
    ],
)
def test_build_legacy_base_tag(
    type_name, runtime_type, dimensions, expected_dimensions
):
    database, cursor = _database()
    try:
        _insert(cursor, 300, type_name, b"")
        _insert(
            cursor,
            200,
            "DataInstance",
            _legacy_rx(cip_type=0x6A, data_instance_id=300, object_id=200),
        )
        _insert(
            cursor,
            100,
            "LegacyTag",
            _legacy_rx(
                data_instance_id=200,
                object_id=100,
                runtime_type=runtime_type,
                attributes=[
                    (0x01, _metadata("LegacyTag", runtime_type, dimensions))
                ],
            ),
        )

        tag = TagBuilder(cursor, 100).build()

        assert tag.name == "LegacyTag"
        assert tag.tag_type == "Base"
        assert tag.data_type == type_name
        assert tag.dimensions == expected_dimensions
        assert tag.radix == "Decimal"
        assert tag.external_access == "Read/Write"
    finally:
        database.close()


def test_build_legacy_message_tag():
    database, cursor = _database()
    try:
        _insert(
            cursor,
            200,
            "MessageData",
            _legacy_rx(cip_type=0x8D, data_instance_id=0, object_id=200),
        )
        _insert(
            cursor,
            100,
            "LegacyMessage",
            _legacy_rx(
                data_instance_id=200,
                object_id=100,
                attributes=[(0x01, _metadata("LegacyMessage"))],
            ),
        )

        assert TagBuilder(cursor, 100).build().data_type == "MESSAGE"
    finally:
        database.close()


@pytest.mark.parametrize(
    "target_class,runtime_type,expected_type",
    [
        (0xB0, 0x8FFD, "MOTION_GROUP"),
        (0xB1, 0x8FC8, "AXIS_SERVO"),
        (0xB1, 0x8FC7, "AXIS_SERVO_DRIVE"),
    ],
)
def test_build_legacy_motion_tag(target_class, runtime_type, expected_type):
    database, cursor = _database()
    try:
        _insert(
            cursor,
            200,
            "MotionData",
            _legacy_rx(cip_type=target_class, object_id=200),
        )
        metadata = bytearray(_metadata("LegacyMotion", runtime_type))
        metadata[0x20F] = 0
        _insert(
            cursor,
            100,
            "LegacyMotion",
            _legacy_rx(
                data_instance_id=200,
                object_id=100,
                attributes=[(0x01, bytes(metadata))],
            ),
        )

        tag = TagBuilder(cursor, 100).build()

        assert tag.data_type == expected_type
        assert tag.radix is None
    finally:
        database.close()


@pytest.mark.parametrize(
    "expected_tag_type,descriptor_length",
    [("Produced", 0x156), ("Produced", 0x316), ("Consumed", 0x150)],
)
def test_build_legacy_produced_and_consumed_tags(
    expected_tag_type, descriptor_length
):
    database, cursor = _database()
    try:
        _insert(cursor, 300, "DINT", b"")
        _insert(
            cursor,
            200,
            "DataInstance",
            _legacy_rx(cip_type=0x6A, data_instance_id=300, object_id=200),
        )
        linked_metadata = struct.pack("<IIII", 4, 3, 0, 2)
        _insert(
            cursor,
            201,
            "LinkedData",
            _legacy_rx(
                cip_type=0x6A,
                object_id=201,
                attributes=[(0x64, linked_metadata)],
            ),
        )

        tag_attributes = [
            (0x01, _metadata("LegacyTag")),
            (0x6B, struct.pack("<I", 201)),
        ]
        if expected_tag_type == "Produced":
            descriptor = bytearray(descriptor_length)
            struct.pack_into("<H", descriptor, 0, 0x0A)
            struct.pack_into("<I", descriptor, 0x16, 0x12345678)
            struct.pack_into("<I", descriptor, 0x1A, 4)
            struct.pack_into("<I", descriptor, 0x1E, 0x12345678)
            struct.pack_into("<H", descriptor, 0x141, 3)
            descriptor[0x144] = 1
            struct.pack_into("<I", descriptor, len(descriptor) - 0x10, 200)
            struct.pack_into(
                "<I", descriptor, len(descriptor) - 0x0C, 536_870_900
            )
            descriptor_attribute = 0x191
        else:
            descriptor = bytearray(0x150)
            struct.pack_into("<H", descriptor, 0, 0x09)
            struct.pack_into("<I", descriptor, 0x02, 500_000)
            struct.pack_into("<H", descriptor, 0x06, 7)
            struct.pack_into("<I", descriptor, 0x08, 0x12345678)
            struct.pack_into("<I", descriptor, 0x0C, 4)
            struct.pack_into("<I", descriptor, 0x10, 0x12345678)
            remote_tag = b"RemoteTag"
            struct.pack_into("<H", descriptor, 0x22, len(remote_tag))
            descriptor[0x24 : 0x24 + len(remote_tag)] = remote_tag
            descriptor[0x143] = 2
            descriptor_attribute = 0x190
            _insert(cursor, 400, "ProducerPLC", b"")
            tag_attributes.insert(1, (0x66, struct.pack("<I", 400)))

        _insert(
            cursor,
            500,
            "ConnectionDescriptor",
            _legacy_rx(
                cip_type=0x7E,
                object_id=500,
                attributes=(
                    [
                        (0x01, bytes(descriptor)),
                        (descriptor_attribute, struct.pack("<I", 100)),
                    ]
                    if descriptor_length == 0x316
                    else [
                        (descriptor_attribute, struct.pack("<I", 100)),
                        (0x01, bytes(descriptor)),
                    ]
                ),
            ),
        )
        _insert(
            cursor,
            100,
            "LegacyTag",
            _legacy_rx(
                data_instance_id=200,
                object_id=100,
                attributes=tag_attributes,
            ),
        )

        tag = TagBuilder(cursor, 100).build()

        assert tag.tag_type == expected_tag_type
        xml = tag.to_xml()
        if expected_tag_type == "Produced":
            assert tag.produce_info.produce_count == "3"
            assert tag.produce_info.minimum_rpi == "0.200"
            assert tag.constant == "false"
            assert 'ProduceCount="3"' in xml
            assert 'MaximumRPI="536870.900"' in xml
        else:
            assert tag.consume_info.producer == "ProducerPLC"
            assert tag.consume_info.remote_tag == "RemoteTag"
            assert tag.consume_info.remote_instance == "7"
            assert 'Producer="ProducerPLC"' in xml
            assert 'RPI="500"' in xml
    finally:
        database.close()


def test_legacy_processor_minimum_rpi():
    database, cursor = _database()
    try:
        metadata = bytearray(48)
        struct.pack_into("<HHH", metadata, 2, 1, 14, 72)
        _insert(
            cursor,
            600,
            "Local",
            _legacy_rx(
                cip_type=0x69,
                object_id=600,
                attributes=[(0x01, bytes(metadata))],
            ),
        )

        assert TagBuilder(cursor)._legacy_processor_minimum_rpi() == 1000
    finally:
        database.close()


def test_build_legacy_alias_tag():
    database, cursor = _database()
    try:
        target_id = 0x44CD5793
        _insert(
            cursor,
            target_id,
            "$Target$",
            _legacy_rx(
                object_id=target_id,
                attributes=[(0x01, _metadata("Automation_Bits"))],
            ),
        )
        alias_path = f"@{target_id:08x}@.11\0".encode("utf-16-le")
        _insert(
            cursor,
            100,
            "LegacyAlias",
            _legacy_rx(
                data_instance_id=target_id,
                object_id=100,
                attributes=[
                    (0x01, _metadata("LegacyAlias", 0xC1)),
                    (0x65, alias_path),
                ],
            ),
        )

        tag = TagBuilder(cursor, 100).build()

        assert tag.tag_type == "Alias"
        assert tag.data_type is None
        assert tag.alias_for == "Automation_Bits.11"
        xml = tag.to_xml()
        assert 'AliasFor="Automation_Bits.11"' in xml
        assert "DataType=" not in xml
    finally:
        database.close()


def test_legacy_alias_rejects_missing_target():
    database, cursor = _database()
    try:
        alias_path = "@44cd5793@.11\0".encode("utf-16-le")
        _insert(
            cursor,
            100,
            "LegacyAlias",
            _legacy_rx(
                data_instance_id=0x44CD5793,
                object_id=100,
                attributes=[
                    (0x01, _metadata("LegacyAlias", 0xC1)),
                    (0x65, alias_path),
                ],
            ),
        )

        with pytest.raises(ValueError, match="target does not exist"):
            TagBuilder(cursor, 100).build()
    finally:
        database.close()


def test_legacy_program_schedule_id_and_task():
    schedule_id = 0x2420
    program = _legacy_rx(
        cip_type=0x68,
        attributes=[
            (0x01, _metadata("MainProgram", schedule_id=schedule_id))
        ],
    )
    assert _program_schedule_id(program) == schedule_id

    task_data = bytearray(806)
    struct.pack_into("<H", task_data, 0, 1)
    struct.pack_into("<I", task_data, 2, schedule_id)
    struct.pack_into("<I", task_data, 514, 10_000)
    struct.pack_into("<H", task_data, 652, 2)
    struct.pack_into("<H", task_data, 654, 5)
    struct.pack_into("<I", task_data, 802, 500_000)
    task_record = _legacy_rx(
        cip_type=0x70,
        attributes=[(0x01, bytes(task_data))],
    )

    database, cursor = _database()
    try:
        _insert(cursor, 100, "MainTask", task_record)
        task = TaskBuilder(cursor, 100).build({schedule_id: "MainProgram"})

        assert task.type == "PERIODIC"
        assert task.rate == "10"
        assert task.priority == "5"
        assert task.watchdog == "500"
        assert [program.name for program in task.scheduled_programs] == ["MainProgram"]
    finally:
        database.close()


def test_legacy_task_rejects_excess_program_count():
    task_data = bytearray(806)
    struct.pack_into("<H", task_data, 0, 129)
    task_record = _legacy_rx(
        cip_type=0x70,
        attributes=[(0x01, bytes(task_data))],
    )
    database, cursor = _database()
    try:
        _insert(cursor, 100, "MainTask", task_record)
        with pytest.raises(ValueError, match="too many scheduled programs"):
            TaskBuilder(cursor, 100).build({})
    finally:
        database.close()
