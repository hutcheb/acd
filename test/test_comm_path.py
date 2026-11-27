import pytest
from acd.l5x.comm_path import decode_comm_path


@pytest.mark.parametrize('text', ['', 'route\\Z', 'route\\Z\0', 'route\\\U0001f600\0'])
def test_full_tail_and_optional_terminator(text):
    assert decode_comm_path(text.encode('utf-16-le')) == (text.rstrip('\0') or None)


@pytest.mark.parametrize('raw', [b'Z', b'\x00\xd8', 'a\0b'.encode('utf-16-le')])
def test_corrupt_text_is_not_replaced_or_truncated(raw):
    with pytest.raises((UnicodeDecodeError, ValueError)):
        decode_comm_path(raw)
