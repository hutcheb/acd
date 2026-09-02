# Maps (vendor, product_type, product_code) → CatalogNumber string.
# Built from Logix-exported L5X files; not stored in the ACD binary.
from typing import Dict, Optional, Tuple

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
