"""Validate the complete counted-attribute contract for supported Rx records.

This does not infer a FAFA convention from four excess bytes. An Rx header,
attribute count, every attribute length and the Rx length independently define
the payload end. An opaque FAFA record is deliberately outside this contract.
"""
import struct


COUNTED_TYPES = {0x68, 0x69, 0x6A, 0x6B, 0x6C, 0x338}


def complete_attributes(raw):
    if len(raw) < 82 or struct.unpack_from('<H', raw, 10)[0] not in COUNTED_TYPES:
        return None
    declared, count = struct.unpack_from('<II', raw, 74)
    if count > (len(raw) - 82) // 8:
        return None
    position, attrs = 82, []
    for _ in range(count):
        if position + 8 > len(raw):
            return None
        key, size = struct.unpack_from('<II', raw, position)
        end = position + 8 + size
        if end > len(raw):
            return None
        attrs.append((key, bytes(raw[position + 8:end])))
        position = end
    if position not in (declared + 74, declared + 78):
        return None
    return position, attrs
