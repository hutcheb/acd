![ACD Tools](https://github.com/Atbash-Labs/acd-plc-serdes/actions/workflows/acd-tools.yml/badge.svg)

## Rockwell ACD Project File Tools

The Rockwell `.ACD` file is an archive file that contains all the files used by RSLogix / Studio 5000 Logix Designer. It consists of version text files, compressed XML metadata, and several proprietary binary database files (`Comps.Dat`, `SbRegion.Dat`, `Comments.Dat`, `Nameless.Dat`).

This library parses those binary databases and exposes the project contents — controller tags, programs, ladder rungs, data types (UDTs), add-on instructions (AOIs), and hardware modules — as Python objects. It can also serialise the parsed project back to an **L5X XML file** that Studio 5000 can import.

> **Compatibility** — Tested against Studio 5000 firmware versions 20–35. Python 3.8+ is supported; Python 3.12+ is recommended.

---

### Installing

```bash
python -m pip install "git+https://github.com/Atbash-Labs/acd-plc-serdes.git"
```

---

### Quick start — parse an ACD file

```python
from acd.api import ImportProjectFromFile

project = ImportProjectFromFile("MyController.ACD").import_project()
controller = project.controller

# Basic controller info
print(controller._name)           # controller name
print(controller.serial_number)   # e.g. "16#AB12_3456"
print(controller.modified_date)

# Iterate controller-scoped tags
for tag in controller.tags:
    print(f"  {tag.name}  ({tag.data_type})  — {tag._comments}")

# Walk programs -> routines -> ladder rungs
for program in controller.programs:
    print(f"\nProgram: {program._name}")
    for routine in program.routines:
        print(f"  Routine: {routine._name}  [{routine.type}]")
        for i, rung in enumerate(routine.rungs):
            print(f"    Rung {i}: {rung}")

# Inspect user-defined data types
for udt in controller.data_types:
    member_names = [m.name for m in udt.members]
    print(f"UDT {udt.name}: {member_names}")

# Inspect add-on instructions
for aoi in controller.aois:
    print(f"AOI {aoi._name}: {len(aoi.routines)} routines, {len(aoi.tags)} params")

# Inspect hardware modules
for module in controller.map_devices:
    print(f"Module {module._name}: vendor={module.vendor_id} "
          f"type={module.product_type} code={module.product_code} slot={module.slot_no}")
```

---

### Convert ACD to L5X

Export the parsed project as an L5X XML file (importable by Studio 5000):

```python
from acd.api import ConvertAcdToL5x

ConvertAcdToL5x("MyController.ACD", "MyController.L5X").extract()
```

The output is pretty-printed by default. Pass `pretty_print=False` for a compact single-line file:

```python
ConvertAcdToL5x("MyController.ACD", "MyController.L5X", pretty_print=False).extract()
```

> **Note** — The L5X serialisation captures tags, programs, routines, rungs, UDTs, and AOIs.
> Hardware module metadata (catalog numbers, connection parameters) is not fully round-tripped because
> Rockwell stores those as opaque CIP identity records in the binary database rather than as strings.

---

### Extract raw database files

Unzip all embedded files (`.Dat`, `.XML`, etc.) to a directory for inspection:

```python
from acd.api import ExtractAcdDatabase

ExtractAcdDatabase("MyController.ACD", "output/").extract()
# output/ now contains Comps.Dat, SbRegion.Dat, Comments.Dat,
#   Nameless.Dat, QuickInfo.XML, TagInfo.XML, XRefs.Dat, ...
```

---

### Extract raw database records to files

Save every individual binary record from the Comps database as its own file,
useful for reverse-engineering the record format:

```python
from acd.api import ExtractAcdDatabaseRecordsToFiles

ExtractAcdDatabaseRecordsToFiles("MyController.ACD", "output/").extract()
```

---

### Dump Comps database as a navigable folder tree

Writes the entire Comps database as a directory tree where each node is a `.dat` file.
A log file records the CIP class and instance for each record:

```python
from acd.api import DumpCompsRecordsToFile

DumpCompsRecordsToFile("MyController.ACD", "output/").extract()
# Produces output/output.log  +  output/<comp_name>/<comp_name>.dat  (recursive)
```

---

### Low-level access via ExportL5x

For direct SQLite access to the parsed ACD databases:

```python
from acd.l5x.export_l5x import ExportL5x

export = ExportL5x("MyController.ACD")

# Raw SQLite cursor — full access to comps, rungs, region_map, comments, nameless tables
cur = export._cur
cur.execute("SELECT comp_name, object_id FROM comps WHERE parent_id=0 AND record_type=256")
row = cur.fetchone()
ctrl_name, ctrl_id = row[0], row[1]

# High-level objects
controller = export.controller
project    = export.project
```

---

### Project structure

```
acd/
├── api.py                  # Public API (ImportProjectFromFile, ConvertAcdToL5x, ...)
├── l5x/
│   ├── export_l5x.py       # ACD -> SQLite -> Python objects
│   └── elements.py         # Dataclasses + Builder classes for all project elements
├── database/               # Binary .Dat file reader
├── record/                 # Record parsers (Comps, SbRegion, Comments, Nameless)
├── generated/              # Kaitai Struct generated parsers (comps, comments, ...)
└── zip/                    # ACD archive extraction
```

---

### Running the tests

```bash
pip install -e ".[dev]"
pytest
```

---

### Developing

Sections of the code are generated from kaitai template (.ksy) files in the resources/templates folder.
These are generated during the install phase.
The python scripts which are generated are located in the acd/generated folder.

### Contributing

Contributions are welcome. Open an issue or pull request on GitHub.

The sample ACD file used by the tests is `resources/CuteLogix.ACD`.
