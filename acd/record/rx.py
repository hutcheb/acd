import struct
from dataclasses import dataclass
from typing import List

from acd.generated.comps.rx_generic import RxGeneric as GeneratedRxGeneric


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
        for index in range(self.count_record):
            if offset + 8 > len(raw):
                raise ValueError("Invalid legacy Rx attribute header")
            attribute_id, length = struct.unpack_from("<II", raw, offset)
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


class RxGeneric:
    @staticmethod
    def from_bytes(raw: bytes):
        raw = bytes(raw)
        if len(raw) >= 82 and struct.unpack_from("<I", raw, 74)[0] == len(raw) - 74:
            return GeneratedRxGeneric.from_bytes(raw)
        if len(raw) >= 32 and struct.unpack_from("<I", raw, 24)[0] in (
            len(raw) - 28,
            len(raw) - 24,
        ):
            return LegacyRxGeneric(raw)
        return GeneratedRxGeneric.from_bytes(raw)
