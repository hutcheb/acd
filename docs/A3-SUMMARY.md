# A3: ACD → L5X Studio 5000 Import — Complete Summary

**Date:** 2026-09-02
**Status:** Code complete, tested, documented. Pending: final Studio v35 import validation.

## The Problem

`hutcheb/acd` converts Rockwell `.ACD` files to L5X. For hardware modules, the ACD
binary stores only the CIP identity triple `(vendor, product_type, product_code)` —
the human-readable catalog number is not in the file. The old code exported
`CatalogNumber=""` for any module not in a hard-coded 37-entry table. Studio 5000
can't resolve an empty catalog number, and the CPU's `ProcessorType` (set from the
root module's catalog number) became a `CIP-…` string that Studio mis-identifies as
`1756-L1` with a "Change Controller Type" warning.

## The Fix (14 commits on `feat/catalog-number-fallback`)

### Five real bugs found via genuine L82E/L81E Studio testing

The user supplied **genuine** `C1756L82E.ACD` / `C1756L81E.ACD` / `C1756L72.ACD`
(firmware 35.11 / Studio v35). Their QuickInfo.DeviceIdentity gave the REAL CIP
identities: **L82E = 1:14:165**, L81E = 1:14:164, L72 = 1:14:93 (in the built-in
table). The real L82E was out of BOTH the catalog and port tables → the definitive
A3 case. Importing the L82E L5X in Studio v35 surfaced five real bugs:

| # | Commit | Bug | Fix |
|---|--------|-----|-----|
| 1 | `3dc1a16` | Wrong `<Controller>` child element order | Build schema order explicitly |
| 2 | `3dc1a16` | Empty `<Ports/>` for out-of-table CPUs | Add L82E/L81E port structures |
| 3 | `342948a` | Missing `<EthernetPort>` descriptor | Emit it for CPUs with integrated Ethernet |
| 4 | `e4f9a0f` | `pretty_print=True` default → blank lines in `<Ports>` | Default to `pretty_print=False` |
| 5 | `12a36cf` + `061166a` | L82E CIP identity mislabelled (1:14:92 → real 1:14:165) | Correct identity + add to built-in catalog |

### Result

A genuine L82E (1:14:165) now converts to `ProcessorType="1756-L82E"` **natively**
(no external catalog needed), with correct ICP + Ethernet ports, the EthernetPort
descriptor, no blank lines, and the schema-correct element order.

## Test Evidence

### acd (133 passed, 2 skipped)
- `test_catalog_numbers.py` — built-in table invariants (41 entries, real L82E/L81E present)
- `test_catalog_external.py` — external catalog loader/merge
- `test_l5x_controller_schema.py` — Controller element order, L82E/L81E ports, pretty-print guard
- `test_dump_fresh_dir.py`, `test_dump_path_sanitize.py` — Windows dump fixes

### workbench (9 pass)
- 4× ACD-open conversion (native L82E/L81E, L72 control, CIP-fallback)
- 2× full open pipelines (`openFile` + `openBuffer` upload path)
- 1× catalog extractor round-trip (`l5x-catalog.js --acd`)
- 2× ACD detection (`looksLikeAcd` unit tests, no checkout needed)

## Studio v35 Validation (pending — user's step)

Four test files in `Desktop\A3_REAL\`:

| File | ProcessorType | Expected in Studio v35 |
|------|--------------|----------------------|
| `L72_clean.L5X` | `1756-L72` (control, in table) | Clean import |
| `L81E_native.L5X` | `1756-L81E` (real, native) | Clean import |
| `L82E_native.L5X` | `1756-L82E` (real, native) | **Clean import — the fix** |
| `CuteLogix_CIP_fallback.L5X` | `CIP-1-14-216` (out of table) | "Change Controller Type" |

**If `L82E_native.L5X` imports cleanly, the A3 story is fully validated end-to-end
with genuine hardware.**

## Branch Status

- **acd** `feat/catalog-number-fallback`: 14 commits (all user), clean worktree, clean
  diff (12 files, 1032 insertions, 39 deletions, no debug code). **Ready for push/PR.**
- **workbench** `feat/online-plc-cip`: 34 commits (all user), clean worktree. **Ready
  for push/PR.**
