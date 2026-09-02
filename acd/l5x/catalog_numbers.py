# Maps (vendor, product_type, product_code) → CatalogNumber string.
# Built from Logix-exported L5X files; not stored in the ACD binary.
import json
from typing import Dict, Optional, Tuple


class CatalogError(ValueError):
    """Raised when an external catalog file is malformed.

    A catalog that fails to validate is a data error the caller can fix, so it
    is surfaced loudly (not swallowed) rather than silently producing wrong
    catalog numbers.
    """

CATALOG_NUMBERS: Dict[Tuple[int, int, int], str] = {
    (1, 0, 18): "ETHERNET-MODULE",
    (1, 0, 28): "RHINOBP-DRIVE-PERIPHERAL-MODULE",
    (1, 7, 11): "1756-IB16",
    (1, 7, 30): "1756-OW16I",
    (1, 7, 34): "1794-IB16/A",
    (1, 7, 35): "1794-OB16/A",
    (1, 7, 37): "1794-OW8/A",
    (1, 7, 156): "1794-IB32/A",
    (1, 7, 397): "5094-IB16/A",
    (1, 7, 399): "5094-OB16/A",
    (1, 10, 7): "1756-IF8/A",
    (1, 10, 25): "1794-IE8/B",
    (1, 10, 26): "1794-OE4/B",
    (1, 10, 153): "1794-IF8IH/A",
    (1, 10, 154): "1794-OF8IH/A",
    (1, 12, 90): "1794-AENT",
    (1, 12, 166): "1756-EN2T",
    (1, 12, 169): "1756-EN2F",
    (1, 12, 258): "1756-EN4TR",
    (1, 12, 261): "1794-AENTR",
    (1, 12, 322): "5094-AEN2TR/A",
    (1, 14, 72): "1769-L33ERM",
    (1, 14, 93): "1756-L72",
    (1, 14, 94): "1756-L73",
    (1, 14, 164): "1756-L81E",
    (1, 14, 165): "1756-L82E",
    (1, 14, 166): "1756-L83E",
    (1, 14, 167): "1756-L84E",
    (1, 14, 168): "1756-L85E",
    (1, 109, 6): "1794-IP4/B",
    (1, 115, 323): "5094-IF8IH/A",
    (1, 115, 324): "5094-OF8IH/A",
    (1, 123, 1168): "PowerFlex 753-NET-E",
    (1, 142, 1168): "PowerFlex 753-ENETR",
    (1, 143, 2192): "PowerFlex 755-EENET",
    (1182, 0, 4162): "Promag_53/A",
    (1182, 0, 4177): "Promass_83/A",
    (1182, 43, 4154): "Promag_100",
    (1182, 43, 4155): "Promass_300_500",
    (1182, 43, 4156): "Promass_300_500",
    (1182, 43, 4170): "Promass_100",
}


def _identity_key_from_any(raw: object) -> Optional[Tuple[int, int, int]]:
    """Coerce a catalog key into an (int, int, int) identity, or None.

    Accepts the two natural JSON shapes: a 3-element array/tuple
    ``[vendor, product_type, product_code]`` or an object
    ``{"vendor": v, "product_type": t, "product_code": c}``. Returns None
    when the shape is unrecognised so the caller can raise a clear error.
    """
    if isinstance(raw, (list, tuple)) and len(raw) == 3:
        try:
            return (int(raw[0]), int(raw[1]), int(raw[2]))
        except (TypeError, ValueError):
            return None
    if isinstance(raw, dict):
        try:
            return (
                int(raw["vendor"]),
                int(raw["product_type"]),
                int(raw["product_code"]),
            )
        except (KeyError, TypeError, ValueError):
            return None
    return None


def load_external_catalog(path: str) -> Dict[Tuple[int, int, int], str]:
    """Load and validate a JSON catalog of CIP identity → catalog number.

    The file is a mapping from an identity triple to a catalog-number string.
    Two key shapes are accepted (per entry, or as a single wrapper):
      * array:  ``{"1:12:166": "1756-EN2T"}`` or ``{"entries": {"1:12:166": ...}}``
      * object: ``{"1:12:166": "1756-EN2T"}`` where the key is
                ``"vendor:product_type:product_code"`` (e.g. ``"1:12:166"``)

    The colon-joined string form is chosen deliberately: identity triples are
    stable, sortable, and unambiguous when written as ``v:t:c``. Every value
    must be a non-empty string; every key must parse as three non-negative
    integers. The result is a plain dict keyed by the (v, t, c) tuple, ready
    to be passed to ``catalog_number_for_identity(table=...)`` or merged over
    ``CATALOG_NUMBERS``.

    This is the extension point for a shared, richer catalog (Rockwell's own
    data, or the module templates aei-logix5000 extracts) so that adding a
    part number is a data change, not a code change.
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    if not isinstance(data, dict):
        raise CatalogError(f"external catalog root must be a JSON object: {path}")
    if "entries" in data and isinstance(data.get("entries"), dict):
        data = data["entries"]

    out: Dict[Tuple[int, int, int], str] = {}
    for key, value in data.items():
        # Allow "_"-prefixed metadata keys (e.g. "_comment") for documentation
        # inside the JSON; they are skipped, not validated, so a file can carry
        # a human-readable note and still load.
        if isinstance(key, str) and key.startswith("_"):
            continue
        identity = _identity_key_from_any(key)
        if identity is None:
            # Try the "v:t:c" string form.
            identity = _parse_colon_key(key)
        if identity is None:
            raise CatalogError(
                f"unrecognised catalog identity key {key!r} in {path}"
            )
        if not isinstance(value, str) or not value.strip():
            raise CatalogError(
                f"catalog value for identity {identity} must be a non-empty "
                f"string in {path}"
            )
        v, t, c = identity
        if v < 0 or t < 0 or c < 0:
            raise CatalogError(f"identity {identity} has a negative component in {path}")
        out[identity] = value.strip()
    return out


def _parse_colon_key(key: object) -> Optional[Tuple[int, int, int]]:
    """Parse a ``"vendor:product_type:product_code"`` string key."""
    if not isinstance(key, str):
        return None
    parts = key.split(":")
    if len(parts) != 3:
        return None
    try:
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        return None


def merge_catalog(
    base: Optional[Dict[Tuple[int, int, int], str]] = None,
    overrides: Optional[Dict[Tuple[int, int, int], str]] = None,
) -> Dict[Tuple[int, int, int], str]:
    """Return a new table = ``base`` with ``overrides`` applied on top.

    ``base`` defaults to the built-in ``CATALOG_NUMBERS``. ``overrides``
    (typically from ``load_external_catalog``) win on any conflicting
    identity. Neither input is mutated.
    """
    base = CATALOG_NUMBERS if base is None else base
    if not overrides:
        return dict(base)
    merged = dict(base)
    merged.update(overrides)
    return merged


def _fallback_catalog_number(identity: Tuple[int, int, int]) -> str:
    """Derive a structured CatalogNumber for a CIP identity not in the table.

    The ACD binary stores hardware identity only as (vendor, product_type,
    product_code) -- the human-readable catalog number is NOT present in the
    file (that is the whole reason this table exists). When the identity is
    unknown we must not emit an empty CatalogNumber: Studio 5000 will reject
    or mis-resolve a module whose CatalogNumber attribute is blank, while the
    raw identity is always known and unambiguous.

    The fallback is a deterministic, self-describing placeholder in the form
    ``CIP-<vendor>-<product_type>-<product_code>``. It is a stable key that
    (a) always round-trips the module's true hardware identity into the L5X,
    (b) is trivially greppable so a missing table entry is obvious, and (c)
    can be matched against the CIP registry (vendor/product type/product code
    are the canonical CIP identity fields) to recover the real catalog number
    offline. Callers that have a richer catalog (e.g. Rockwell's own) should
    override ``CATALOG_NUMBERS`` or call this helper with their own table.
    """
    vendor, product_type, product_code = identity
    return f"CIP-{vendor}-{product_type}-{product_code}"


def catalog_number_for_identity(
    identity: Tuple[int, int, int],
    table: Optional[Dict[Tuple[int, int, int], str]] = None,
    *,
    fallback: Optional[str] = None,
) -> str:
    """Resolve the CatalogNumber string for a CIP identity triple.

    Resolution order:
      1. the ``table`` (default: the built-in ``CATALOG_NUMBERS``), or
      2. a caller-supplied ``fallback`` string, or
      3. a structured ``CIP-<vendor>-<type>-<code>`` placeholder.

    To use a richer/shared catalog (Rockwell's own data, or the module
    templates aei-logix5000 extracts), load it with
    :func:`load_external_catalog`, combine it with :func:`merge_catalog`
    (external entries win), and pass the result as ``table=``::

        from acd.l5x.catalog_numbers import (
            load_external_catalog, merge_catalog,
        )
        table = merge_catalog(None, load_external_catalog("shared_catalog.json"))
        number = catalog_number_for_identity((1, 14, 216), table=table)

    A zero identity ``(0, 0, 0)`` means the module record did not carry a
    CIP identity at all (e.g. an unparseable record); for that case an empty
    string is returned rather than a fabricated identity, so the caller can
    distinguish "no identity present" from "identity present but unknown".

    This is the single choke point for catalog resolution: ``ModuleBuilder``
    calls it instead of indexing ``CATALOG_NUMBERS`` directly, so adding a
    better catalog (or a CIP-registry lookup) is a one-line change here and
    every module benefits.
    """
    if table is None:
        table = CATALOG_NUMBERS
    if identity == (0, 0, 0):
        return ""
    if identity in table:
        return table[identity]
    if fallback is not None:
        return fallback
    return _fallback_catalog_number(identity)
