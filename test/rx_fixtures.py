"""Builders for synthetic Rx records and the in-memory tables the builders read."""

import sqlite3
import struct

ENVELOPE_MAGIC = 0x0AAA96AA


def comps_database():
    """An in-memory database with the comps and comments tables."""
    connection = sqlite3.connect(":memory:")
    cursor = connection.cursor()
    cursor.execute(
        "CREATE TABLE comps(object_id int, parent_id int, comp_name text, "
        "seq_number int, record_type int, record BLOB NOT NULL)"
    )
    cursor.execute(
        "CREATE TABLE comments(seq_number int, sub_record_length int, "
        "object_id int, record_string text, record_type int, parent int, "
        "tag_reference text, rung_content int, member_ref int)"
    )
    return connection, cursor


def insert_comp(cursor, object_id, name, record, parent_id=0, record_type=256):
    cursor.execute(
        "INSERT INTO comps VALUES (?, ?, ?, ?, ?, ?)",
        (object_id, parent_id, name, 0, record_type, record),
    )


def rx_header(cip_type: int, comment_id: int = 0, main: bytes = bytes(60), unknown: int = 0) -> bytes:
    """The 14-byte current-layout header followed by the 60-byte main record."""
    return struct.pack("<IIHHH", 0, 0, unknown, cip_type, comment_id) + main


def rx_record(cip_type: int, comment_id: int, attributes: bytes, count: int, length_extra: int = 4) -> bytes:
    """A current-layout record: header, stored length, attribute count, attributes."""
    return rx_header(cip_type, comment_id, unknown=0x10) + struct.pack(
        "<II", len(attributes) + length_extra, count
    ) + attributes


def protected_rx_record(cip_type: int, comment_id: int = 0, main: bytes = bytes(60), unknown: int = 0x10) -> bytes:
    """A readable header with the encrypted envelope in place of the attributes."""
    envelope = struct.pack("<II", ENVELOPE_MAGIC, 0xA0000010) + bytes(range(0x80, 0xC0))
    return rx_header(cip_type, comment_id, main, unknown) + struct.pack("<I", 0x40) + envelope
