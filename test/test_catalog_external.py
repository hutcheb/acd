"""Tests for the external catalog loader/merge (the shared-catalog extension
point that lets Ben/Juan add part numbers as data, not code).

Pure-function, no ACD file, no build/ dir -- same style as
test_catalog_numbers.py.
"""
import json

import pytest

from acd.l5x.catalog_numbers import (
    CATALOG_NUMBERS,
    CatalogError,
    catalog_number_for_identity,
    load_external_catalog,
    merge_catalog,
)


def test_load_colon_key_form(tmp_path):
    p = tmp_path / "cat.json"
    p.write_text(json.dumps({"1:12:166": "1756-EN2T", "1:99:4242": "MY-MOD"}), encoding="utf-8")
    cat = load_external_catalog(str(p))
    assert cat == {(1, 12, 166): "1756-EN2T", (1, 99, 4242): "MY-MOD"}


def test_load_array_key_form(tmp_path):
    p = tmp_path / "cat.json"
    # Array keys are accepted too.
    p.write_text(
        json.dumps([[[1, 12, 166], "1756-EN2T"], [[1, 99, 4242], "MY-MOD"]]),
        encoding="utf-8",
    )
    # An array-of-pairs is NOT the object form; the root must be an object.
    with pytest.raises(CatalogError):
        load_external_catalog(str(p))


def test_load_entries_wrapper(tmp_path):
    p = tmp_path / "cat.json"
    p.write_text(
        json.dumps({"entries": {"1:12:166": "1756-EN2T"}}), encoding="utf-8"
    )
    cat = load_external_catalog(str(p))
    assert cat == {(1, 12, 166): "1756-EN2T"}


def test_load_rejects_bad_value(tmp_path):
    p = tmp_path / "cat.json"
    p.write_text(json.dumps({"1:12:166": 12345}), encoding="utf-8")
    with pytest.raises(CatalogError):
        load_external_catalog(str(p))


def test_load_rejects_bad_key(tmp_path):
    p = tmp_path / "cat.json"
    p.write_text(json.dumps({"not:a:triple": "X"}), encoding="utf-8")
    with pytest.raises(CatalogError):
        load_external_catalog(str(p))


def test_merge_overrides_builtin_and_keeps_rest():
    overrides = {(1, 99, 4242): "PATCHED-MOD"}
    merged = merge_catalog(CATALOG_NUMBERS, overrides)
    # Built-in entry still present.
    assert merged[(1, 12, 166)] == CATALOG_NUMBERS[(1, 12, 166)]
    # Override added.
    assert merged[(1, 99, 4242)] == "PATCHED-MOD"
    # The built-in table itself was not mutated.
    assert (1, 99, 4242) not in CATALOG_NUMBERS


def test_external_catalog_wins_in_resolution():
    # A merged table fed to the resolver makes an external entry resolve
    # instead of the CIP-... placeholder.
    overrides = {(1, 99, 4242): "MY-MOD"}
    merged = merge_catalog(CATALOG_NUMBERS, overrides)
    assert catalog_number_for_identity((1, 99, 4242), table=merged) == "MY-MOD"
    # Unknown identity still falls back.
    assert catalog_number_for_identity((1, 88, 777), table=merged) == "CIP-1-88-777"


def test_metadata_keys_are_skipped(tmp_path):
    # "_"-prefixed keys are documentation, not catalog entries, and must be
    # ignored (so the bundled example file with a "_comment" loads cleanly).
    p = tmp_path / "cat.json"
    p.write_text(
        json.dumps({"_comment": "example", "1:12:166": "1756-EN2T"}), encoding="utf-8"
    )
    cat = load_external_catalog(str(p))
    assert cat == {(1, 12, 166): "1756-EN2T"}


def test_bundled_example_file_loads():
    # The shipped example file must itself be valid and loadable.
    import os
    example = os.path.join("..", "resources", "external_catalog.example.json")
    if not os.path.exists(example):
        pytest.skip("example file not present in this checkout")
    cat = load_external_catalog(example)
    # It carries the two verifiable entries from the bundled L5X samples.
    assert cat.get((1, 12, 166)) == "1756-EN2T"
    assert cat.get((1, 14, 168)) == "1756-L85E"


def test_full_load_and_resolve_flow(tmp_path):
    # The realistic flow: drop a JSON catalog in, load, merge, resolve.
    p = tmp_path / "shared_catalog.json"
    p.write_text(json.dumps({"1:14:216": "1756-L83E-EXAMPLE"}), encoding="utf-8")
    merged = merge_catalog(CATALOG_NUMBERS, load_external_catalog(str(p)))
    # 1/14/216 was NOT in the built-in table (it's the CuteLogix CPU case);
    # with the external catalog it now resolves to a real name.
    assert catalog_number_for_identity((1, 14, 216), table=merged) == "1756-L83E-EXAMPLE"
