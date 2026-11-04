import struct
from dataclasses import dataclass
from typing import List

from acd.generated.comps.rx_generic import RxGeneric as GeneratedRxGeneric

# Source protection stores a record's attribute block as an encrypted
# envelope. The envelope starts with this u32 where a plain record has its
# attribute count (offset 78, right after the 60-byte main record and the
# length field); the main record before it stays readable.
ENCRYPTED_ENVELOPE_MAGIC = 0x0AAA96AA


@dataclass
class LegacyAttributeRecord:
    attribute_id: int
    len_value: int
    value: bytes


class LegacyMainRecord:
    def __init__(self, raw: bytes, attributes: List[LegacyAttributeRecord]):
        self.body = raw
        self.runtime_type = struct.unpack_from("<I", raw, 4)[0]
        self.data_type = self.runtime_type
        self.cip_data_type = self.runtime_type & 0xFFFF
        self.dimension_1 = 0
        self.dimension_2 = 0
        self.dimension_3 = 0
        self.radix = 0
        self.external_access = 0
        self.data_table_instance = 0

        metadata = next(
            (attribute.value for attribute in attributes if attribute.attribute_id == 0x01),
            b"",
        )
        if len(metadata) >= 0x220:
            self.runtime_type = struct.unpack_from("<H", metadata, 0x100)[0]
            self.data_type = self.runtime_type
            self.cip_data_type = self.runtime_type
            self.data_table_instance = struct.unpack_from("<I", metadata, 0x102)[0]
            self.radix = metadata[0x20F] >> 4
            self.dimension_1, self.dimension_2, self.dimension_3 = struct.unpack_from(
                "<III", metadata, 0x212
            )
            self.external_access = struct.unpack_from("<H", metadata, 0x21E)[0]


class LegacyRxGeneric:
    # Legacy records are never source-protected.
    protected = False

    def __init__(self, raw: bytes):
        self.is_legacy = True
        self.data_instance_id, self.unique_tag_identifier = struct.unpack_from(
            "<II", raw, 0
        )
        # Keep the generated parser's attribute for callers that consume the
        # common interface. In this layout it references tag data, not scope.
        self.parent_id = self.data_instance_id
        self.record_format_version = 0
        self.cip_type, self.comment_id = struct.unpack_from("<HH", raw, 8)
        self.object_id = struct.unpack_from("<I", raw, 20)[0]
        self.record_buffer = raw[14:74]
        self.len_record, self.count_record = struct.unpack_from("<II", raw, 24)
        self.extended_records: List[LegacyAttributeRecord] = []

        offset = 32
        # Like the LastAttributeRecord of the generated layout, the last
        # attribute declares 4 bytes more than the record holds.  With a short
        # value (e.g. an empty CommPath 0x6A of length 2) the missing bytes
        # already cut into the attribute header, so read the header from a
        # zero-padded copy and let the length check below decide.
        padded = raw + b"\x00" * 4
        for index in range(self.count_record):
            last = index == self.count_record - 1
            if offset + 8 > len(raw) + (4 if last else 0):
                raise ValueError("Invalid legacy Rx attribute header")
            attribute_id, length = struct.unpack_from("<II", padded, offset)
            value_end = offset + 8 + length
            if value_end > len(raw):
                if index == self.count_record - 1 and value_end == len(raw) + 4:
                    value_end = len(raw)
                else:
                    raise ValueError("Invalid legacy Rx attribute length")
            self.extended_records.append(
                LegacyAttributeRecord(attribute_id, length, raw[offset + 8 : value_end])
            )
            offset = value_end
        if offset != len(raw):
            raise ValueError("Invalid legacy Rx record length")

        self.main_record = LegacyMainRecord(raw[12:24], self.extended_records)

    @property
    def logical_name(self):
        metadata = next(
            (
                attribute.value
                for attribute in self.extended_records
                if attribute.attribute_id == 0x01
            ),
            b"",
        )
        if len(metadata) < 2:
            return ""
        length = struct.unpack_from("<H", metadata, 0)[0]
        if length > len(metadata) - 2:
            return ""
        return metadata[2 : 2 + length].decode("utf-8", errors="replace")


class CurrentRxGeneric(GeneratedRxGeneric):
    """The current-layout Rx record, read by the generated parser."""

    # True for a source-protected record: only the header and main record
    # are readable, and extended_records is empty.
    protected = False


class RxGeneric:
    @staticmethod
    def from_bytes(raw: bytes, allow_protected: bool = False):
        """Parse an Rx record of either layout.

        A source-protected record raises ValueError unless `allow_protected`
        is set; then it parses to its header and main record only, with
        `protected` set.
        """
        raw = bytes(raw)
        if len(raw) >= 82:
            stored_length, count = struct.unpack_from("<II", raw, 74)
            if count == ENCRYPTED_ENVELOPE_MAGIC:
                if not allow_protected:
                    raise ValueError("Rx record is source-protected (encrypted)")
                # Read the header and main record only (as a record with no
                # attributes); the attributes are encrypted.
                parsed = CurrentRxGeneric.from_bytes(raw[:78] + bytes(4))
                parsed.protected = True
                return parsed
            if stored_length == len(raw) - 74:
                return CurrentRxGeneric.from_bytes(raw)
        if len(raw) >= 32 and struct.unpack_from("<I", raw, 24)[0] in (
            len(raw) - 28,
            len(raw) - 24,
        ):
            return LegacyRxGeneric(raw)
        return CurrentRxGeneric.from_bytes(raw)
