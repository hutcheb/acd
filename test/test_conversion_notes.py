from pathlib import Path
import sqlite3
import struct
import xml.etree.ElementTree as ET

import pytest

from acd.l5x.conversion_notes import ConversionNotes, xml_comment
from acd.l5x.elements import RoutineBuilder, TagBuilder
from acd.l5x.export_l5x import ExportL5x
from .test_rx import _database as _rx_database, _insert, _legacy_rx, _metadata

PROJECT = Path("..") / "resources" / "ACDTestsWithAOI.ACD"
XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'


def _database():
    # test_rx's database plus the rung tables RoutineBuilder and the Region
    # Map repair read.
    database, cursor = _rx_database()
    cursor.execute("CREATE TABLE rungs(object_id int, rung text, seq_number int)")
    cursor.execute(
        "CREATE TABLE region_map(object_id int, parent_id int, unknown int, "
        "seq_no int, record BLOB NOT NULL)"
    )
    return database, cursor


def _controller_tags(exporter):
    cursor = exporter._cur
    cursor.execute("SELECT object_id FROM comps WHERE parent_id=0 AND record_type=256")
    (controller_id,) = cursor.fetchone()
    cursor.execute(
        "SELECT object_id FROM comps WHERE parent_id=? AND comp_name='RxTagCollection'",
        (controller_id,),
    )
    (collection_id,) = cursor.fetchone()
    cursor.execute(
        "SELECT object_id, comp_name FROM comps WHERE parent_id=? ORDER BY object_id",
        (collection_id,),
    )
    return cursor.fetchall()


def test_xml_comment_empty_list_is_empty_string():
    assert xml_comment([]) == ""


def test_xml_comment_cleans_line_breaks_illegal_characters_and_double_hyphens():
    out = xml_comment(["first\nline", "bad\x01char -- here", "--"])

    assert out == (
        "<!-- acd-tools conversion notes:\n"
        "first line\n"
        "badchar - here\n"
        "-\n"
        "-->\n"
    )
    ET.fromstring(f"<root>{out}</root>")


def test_conversion_notes_add_warn_and_current():
    notes = ConversionNotes()
    notes.add("first")
    notes.warn("second", "technical detail")

    current = notes.current()

    assert current == ["first", "second"]
    current.append("changed")
    assert notes.current() == ["first", "second"]


def test_clean_export_has_no_notes():
    project = ExportL5x(PROJECT).project

    assert project.conversion_notes == []
    assert "conversion notes" not in project.to_xml()


def test_controller_tag_fallback_is_recorded_in_project_and_xml(monkeypatch):
    exporter = ExportL5x(PROJECT)
    target_id, target_name = _controller_tags(exporter)[0]
    original_build = TagBuilder.build

    def build_or_fail(self):
        if self._object_id == target_id:
            raise ValueError("injected test failure")
        return original_build(self)

    monkeypatch.setattr(TagBuilder, "build", build_or_fail)

    project = exporter.project

    assert project.conversion_notes == [
        f"Tag '{target_name}' could not be read and was left out"
    ]
    xml = project.to_xml()
    assert xml.startswith("<!-- acd-tools conversion notes:\n")
    ET.fromstring(XML_DECLARATION + xml)


def test_grouped_notes_list_a_few_names_and_a_count():
    notes = ConversionNotes()
    notes.add("before")
    for index in range(7):
        notes.warn_grouped("Routines exported as RLL", "R%d" % index)
    notes.add("after")
    notes.warn_grouped("Tags left out", "T")

    assert notes.current() == [
        "before",
        "Routines exported as RLL: 'R0', 'R1', 'R2', 'R3', 'R4' and 2 more",
        "after",
        "Tags left out: 'T'",
    ]


def test_conversions_do_not_share_notes():
    first = ExportL5x(PROJECT)
    second = ExportL5x(PROJECT)

    assert first._notes is not second._notes
    first._notes.add("recorded only for the first conversion")
    assert second._notes.current() == []


def test_produced_tag_without_connection_info_becomes_base_and_is_noted():
    database, cursor = _database()
    try:
        _insert(cursor, 300, "DINT", b"")
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
                attributes=[
                    (0x01, _metadata("LegacyTag")),
                    (0x6B, struct.pack("<I", 999)),
                ],
            ),
        )
        notes = ConversionNotes()

        tag = TagBuilder(cursor, 100, _notes=notes).build()

        assert tag.tag_type == "Base"
        assert notes.current() == [
            "Tag 'LegacyTag': produced connection info could not be read; "
            "exported as a Base tag"
        ]
    finally:
        database.close()


def test_region_map_0x4e_guess_is_noted():
    record = bytearray(0x4E + 32)
    struct.pack_into("<I", record, 0x18, 999)
    struct.pack_into("<I", record, 0x4A, 999)
    notes = ConversionNotes()

    ExportL5x._parse_region_map(bytes(record), {999999}, notes=notes)

    recorded = notes.current()
    assert len(recorded) == 1
    assert "0x4E" in recorded[0]


@pytest.mark.parametrize(
    "rung_ids,region_entries,pending,expected_notes",
    [
        # One unclaimed rung fits the gap, so it is restored and nothing is noted.
        ([10, 11, 12], [(10, 5, 0, 1), (12, 5, 0, 3)], [(5, 0, 2)], []),
        # Two unclaimed rungs fit the gap, so the rung is unknown.
        (
            [10, 11, 12, 13],
            [(10, 5, 0, 1), (13, 5, 0, 4)],
            [(5, 0, 2)],
            [
                "Routine 'MainRoutine': a truncated Region Map entry (seq 2) could "
                "be any of 2 rungs; that rung will be missing from the export"
            ],
        ),
        # No unclaimed rung fits the gap.
        (
            [10],
            [(10, 5, 0, 1)],
            [(5, 0, 2)],
            [
                "Routine 'MainRoutine': a truncated Region Map entry (seq 2) could "
                "not be matched to any unclaimed rung, so no rung is known to be "
                "missing"
            ],
        ),
    ],
)
def test_truncated_region_map_entry_notes(
    rung_ids, region_entries, pending, expected_notes
):
    exporter = ExportL5x.__new__(ExportL5x)
    database = sqlite3.connect(":memory:")
    cursor = database.cursor()
    cursor.execute("CREATE TABLE rungs(object_id int, rung text, seq_number int)")
    cursor.execute(
        "CREATE TABLE region_map(object_id int, parent_id int, unknown int, "
        "seq_no int, record BLOB NOT NULL)"
    )
    cursor.executemany(
        "INSERT INTO rungs VALUES (?, ?, ?)",
        [(object_id, "", 0) for object_id in rung_ids],
    )
    cursor.executemany(
        "INSERT INTO region_map VALUES (?, ?, ?, ?, ?)",
        [(object_id, parent, unknown, seq, b"") for object_id, parent, unknown, seq in region_entries],
    )
    exporter._db = database
    exporter._cur = cursor
    exporter._pending_region_map_gaps = pending
    exporter._id_to_name = {5: "MainRoutine"}
    exporter._notes = ConversionNotes()
    try:
        exporter._repair_region_map_gaps()

        assert exporter._notes.current() == expected_notes
    finally:
        database.close()


@pytest.mark.parametrize(
    "type_value,expected_type,expected_notes",
    [
        (0, "RLL", ["Routines with no readable type but with ladder rungs, exported as RLL: 'MainRoutine'"]),
        (1, "RLL", []),
    ],
)
def test_typeless_routine_with_rungs_is_noted(type_value, expected_type, expected_notes):
    raw = bytearray(_legacy_rx(attributes=[(0x01, bytes(60))]))
    # The routine type sits at offset 0x30 of the record buffer, which starts at byte 14.
    struct.pack_into("<H", raw, 14 + 0x30, type_value)
    database, cursor = _database()
    try:
        _insert(cursor, 100, "MainRoutine", bytes(raw))
        cursor.execute("INSERT INTO rungs VALUES (?, ?, ?)", (500, "NOP();", 1))
        cursor.execute(
            "INSERT INTO region_map VALUES (?, ?, ?, ?, ?)", (500, 100, 0, 1, b"")
        )
        notes = ConversionNotes()

        routine = RoutineBuilder(cursor, 100, _notes=notes).build()

        assert routine.type == expected_type
        assert routine.rungs == ["NOP();"]
        assert notes.current() == expected_notes
    finally:
        database.close()
