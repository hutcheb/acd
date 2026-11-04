import struct

from acd.l5x.conversion_notes import ConversionNotes
from acd.l5x.elements import AoiBuilder, RoutineBuilder
from acd.record.rx import RxGeneric

from .rx_fixtures import comps_database, protected_rx_record, rx_record


def _cursor():
    connection, cur = comps_database()
    data_type = rx_record(0x6C, 0x0123, struct.pack("<II", 1, 4) + b"\x00" * 4, 1)
    cur.executemany(
        "INSERT INTO comps VALUES (?, ?, ?, ?, ?, ?)",
        [
            (2, 1, "RxUDIDefinitionCollection", 0, 0, b"aois"),
            (3, 1, "RxDataTypeCollection", 0, 0, b"types"),
            (10, 2, "Widget", 0, 256, protected_rx_record(0x338, 0x4242)),
            (11, 3, "Widget", 0, 256, data_type),
        ],
    )
    cur.executemany(
        "INSERT INTO comments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            # Type-1 rows hold user text only when object_id is 1.
            (0, 20, 7, "Internal string", 1, 0x0123006C, "", 0, 0),
            (0, 20, 1, "Moves a widget", 1, 0x0123006C, "", 0, 0),
            (0, 20, 1, "A parameter note", 1, 0x0123006C, "", 0, 0x55AA),
        ],
    )
    return connection, cur


def test_rx_reads_envelope_marker():
    # Only callers that handle protection opt in; for the rest the record
    # is unreadable.
    try:
        RxGeneric.from_bytes(protected_rx_record(0x338, 0x4242))
        raise AssertionError("a protected record parsed without opting in")
    except ValueError:
        pass
    protected = RxGeneric.from_bytes(protected_rx_record(0x338, 0x4242), allow_protected=True)
    assert protected.protected
    assert (protected.cip_type, protected.comment_id, protected.extended_records) == (0x338, 0x4242, [])
    plain = rx_record(0x338, 0x4242, struct.pack("<II", 1, 4) + b"\x00" * 4, 1)
    assert not RxGeneric.from_bytes(plain).protected
    # A record too short to hold the marker is never read as protected.
    try:
        short = RxGeneric.from_bytes(b"short", allow_protected=True)
    except Exception:
        short = None
    assert short is None or not short.protected


def test_protected_aoi_exports_only_readable_fields():
    from loguru import logger

    connection, cur = _cursor()
    warnings = []
    sink = logger.add(warnings.append, level="WARNING")
    try:
        xml = AoiBuilder(cur, 10).build().to_xml()
    finally:
        logger.remove(sink)
        connection.close()
    assert xml == (
        '<AddOnInstructionDefinition Name="Widget">'
        "<Description>\n<![CDATA[Moves a widget]]>\n</Description>"
        "<Routines></Routines></AddOnInstructionDefinition>"
    )
    assert len(warnings) == 1
    assert "'Widget' is source-protected" in warnings[0]


def test_protected_aoi_description_with_cdata_end_marker():
    import xml.etree.ElementTree as ET

    connection, cur = _cursor()
    cur.execute(
        "UPDATE comments SET record_string=? WHERE record_string=?",
        ("a]]>b", "Moves a widget"),
    )
    try:
        xml = AoiBuilder(cur, 10).build().to_xml()
    finally:
        connection.close()
    assert ET.fromstring(xml).findtext("Description").strip() == "a]]>b"


def test_protected_aoi_is_recorded_in_project_notes():
    connection, cur = _cursor()
    notes = ConversionNotes()
    try:
        AoiBuilder(cur, 10, _notes=notes).build()
    finally:
        connection.close()

    assert notes.current() == [
        "Add-On Instruction 'Widget' is source-protected: its revision, vendor, "
        "dates, help text, parameters and local tags are encrypted and were left "
        "out; only its name, description and routine names were exported"
    ]


def test_protected_routine_is_recorded_in_project_notes():
    connection, cur = _cursor()
    cur.executemany(
        "INSERT INTO comps VALUES (?, ?, ?, ?, ?, ?)",
        [
            (12, 10, "RxRoutineCollection", 0, 0, b"routines"),
            (13, 12, "Main", 0, 256, protected_rx_record(0x338, 0x4343)),
        ],
    )
    notes = ConversionNotes()
    try:
        RoutineBuilder(cur, 13, _notes=notes).build()
    finally:
        connection.close()

    assert notes.current() == [
        "Routines whose content could not be read (likely source-protected), "
        "exported with no rungs: 'Widget/Main'"
    ]
