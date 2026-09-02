"""Tests for catalog number resolution (ACD -> L5X hardware round-trip).

These are pure-function tests (no ACD file, no shared build/ temp dir) so they
run reliably on Windows, matching the style of test_elements_helpers.py.

Background: the ACD binary stores hardware identity only as
(vendor, product_type, product_code); the human-readable catalog number is not
in the file. ModuleBuilder resolves it via catalog_number_for_identity(). The
historical bug: any identity missing from the hard-coded CATALOG_NUMBERS table
emitted CatalogNumber="", losing the module's hardware identity from the L5X.
"""
from acd.l5x.catalog_numbers import (
    CATALOG_NUMBERS,
    catalog_number_for_identity,
)


def test_known_identity_resolves_from_table():
    # (1, 12, 166) is 1756-EN2T in the built-in table.
    assert catalog_number_for_identity((1, 12, 166)) == "1756-EN2T"
    # And the resolution matches the table directly, so we did not change
    # behaviour for modules that were already correct.
    assert catalog_number_for_identity((1, 12, 166)) == CATALOG_NUMBERS[(1, 12, 166)]


def test_unknown_identity_gets_structured_cip_fallback_not_empty():
    # A valid but unlisted identity must NOT degrade to "".
    unknown = (1, 99, 4242)
    assert unknown not in CATALOG_NUMBERS
    result = catalog_number_for_identity(unknown)
    assert result != ""
    # The fallback is a deterministic, self-describing placeholder that
    # round-trips the true CIP identity.
    assert result == "CIP-1-99-4242"


def test_zero_identity_returns_empty():
    # (0, 0, 0) means the record carried no CIP identity at all (unparseable
    # record path in ModuleBuilder). We must not fabricate a "CIP-0-0-0"
    # identity for a module that has none.
    assert catalog_number_for_identity((0, 0, 0)) == ""


def test_caller_table_overrides_builtin():
    # A richer/patched catalog takes precedence over the built-in table.
    custom = {(1, 12, 166): "CUSTOM-EN2T", (1, 99, 4242): "MY-MODULE"}
    assert catalog_number_for_identity((1, 12, 166), table=custom) == "CUSTOM-EN2T"
    # Identity present in the custom table but not the built-in one.
    assert catalog_number_for_identity((1, 99, 4242), table=custom) == "MY-MODULE"


def test_explicit_fallback_string_used_for_unknown():
    # A caller-supplied fallback is used before the CIP placeholder.
    assert catalog_number_for_identity((1, 99, 4242), fallback="?") == "?"
    # But a known identity still resolves from the table, not the fallback.
    assert catalog_number_for_identity((1, 12, 166), fallback="?") == "1756-EN2T"


def test_fallback_is_deterministic():
    # Same identity, same string -- the placeholder is stable across runs so
    # an L5X diff is meaningful when only a table entry is added.
    assert catalog_number_for_identity((1, 99, 4242)) == catalog_number_for_identity((1, 99, 4242))


def test_builtin_table_invariants():
    # Regression guard on the built-in CATALOG_NUMBERS: lock its shape so a
    # future edit that accidentally drops, corrupts, or mis-types an entry is
    # caught. This tests what the table IS (honest, not a guess) -- every key
    # is a 3-tuple of non-negative ints, every value a non-empty string, and
    # the table is the documented size. (Note: two distinct triples may share
    # a catalog value -- e.g. firmware variants of the same device -- which is
    # legitimate and NOT flagged here.)
    assert len(CATALOG_NUMBERS) == 39, "built-in table size changed: %d" % len(CATALOG_NUMBERS)
    for key, value in CATALOG_NUMBERS.items():
        assert isinstance(key, tuple) and len(key) == 3, "key must be a 3-tuple: %r" % (key,)
        for component in key:
            assert isinstance(component, int) and component >= 0, "key component must be a non-negative int: %r" % (key,)
        assert isinstance(value, str) and value.strip(), "value must be a non-empty string: %r -> %r" % (key, value)
