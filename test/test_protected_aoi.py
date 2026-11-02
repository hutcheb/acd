import struct

from acd.record.rx import RxGeneric

from .rx_fixtures import protected_rx_record, rx_record


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
