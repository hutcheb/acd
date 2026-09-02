"""Tests for _sanitize_path_component (Windows-safe Comps dump paths).

Pure-function tests (no ACD file, no build/ temp dir), same style as
test_elements_helpers.py.

Background: DumpCompsRecords writes one sub-directory and one <name>.dat per
Comps record, naming them after comp_name. Logix comp_names can contain ":"
(channel names like "CHANNEL_DI_TIMESTAMP:O:0") and other characters that are
illegal in Windows filenames, which made os.makedirs/open raise
OSError [WinError 123] on Windows. The sanitizer maps those to safe
characters while leaving already-safe names untouched.
"""
from acd.l5x.elements import _sanitize_path_component


def test_plain_name_unchanged():
    # Names with no path-unsafe characters must pass through untouched, so
    # existing dumps on Linux/macOS are unaffected.
    assert _sanitize_path_component("MainProgram") == "MainProgram"
    assert _sanitize_path_component("RxTagCollection") == "RxTagCollection"


def test_colons_replaced():
    # The real-world failure: a channel/tag name with ":" in it.
    assert _sanitize_path_component("CHANNEL_DI_TIMESTAMP:O:0") == (
        "CHANNEL_DI_TIMESTAMP_O_0"
    )
    # Single colon.
    assert _sanitize_path_component("tag:member") == "tag_member"


def test_slashes_and_backslashes_replaced():
    # Member-access separators are also illegal in filesystem names.
    assert _sanitize_path_component("a/b") == "a_b"
    assert _sanitize_path_component("a\\b") == "a_b"


def test_windows_reserved_chars_replaced():
    for ch in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
        assert ch not in _sanitize_path_component("x" + ch + "y")


def test_control_chars_replaced():
    assert _sanitize_path_component("a\x00b\x1fc") == "a_b_c"


def test_trailing_space_and_dot_stripped():
    # open() on Windows fails on trailing spaces/dots in a name.
    assert _sanitize_path_component("name ") == "name"
    assert _sanitize_path_component("name.") == "name"


def test_windows_device_names_prefixed():
    # CON/NUL/COM1 etc. are reserved on Windows; prefix so they open fine.
    assert _sanitize_path_component("CON") == "_CON"
    assert _sanitize_path_component("NUL") == "_NUL"
    assert _sanitize_path_component("COM1") == "_COM1"
    # Non-reserved names that merely *start* with a reserved prefix are fine.
    assert _sanitize_path_component("COMFORT") == "COMFORT"


def test_all_illegal_becomes_underscore_not_empty():
    # A name that is entirely illegal must not collapse to "" (an empty path
    # component is itself a problem). Each illegal char maps 1:1 to "_".
    assert _sanitize_path_component("::") == "__"
    assert _sanitize_path_component("::") != ""


def test_is_deterministic():
    # Same input, same output -- stable across runs.
    assert _sanitize_path_component("CHANNEL_DI_TIMESTAMP:O:0") == _sanitize_path_component(
        "CHANNEL_DI_TIMESTAMP:O:0"
    )
