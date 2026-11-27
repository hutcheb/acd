"""Validate the complete counted-attribute contract for supported Rx records.

These bounds checks do not identify a layout. Inflated final-attribute lengths
and outer trailers can mimic complete counted attributes. Recovery requires an
explicit caller assertion of the complete-counted contract; compat is default.
Opaque FAFA records are deliberately outside this contract.
"""
import struct
from contextlib import contextmanager
from contextvars import ContextVar

_LAYOUT = ContextVar('acd_rx_attribute_layout', default='compat')


def counted_layout_enabled():
    return _LAYOUT.get() == 'complete-counted'


@contextmanager
def attribute_layout(name=None):
    """Caller assertion, not autodetection: outer trailers can mimic values."""
    if name is None:
        yield
        return
    if name not in ('compat', 'complete-counted'):
        raise ValueError('Unknown Rx attribute layout')
    token = _LAYOUT.set(name)
    try:
        yield
    finally:
        _LAYOUT.reset(token)


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
    if len(raw) - position not in (0, 4):
        return None
    if len({key for key, value in attrs}) != len(attrs):
        raise ValueError('Duplicate counted Rx attribute identity')
    return position, attrs
