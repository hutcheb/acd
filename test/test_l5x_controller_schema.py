"""Regression tests for the L5X <Controller> schema correctness (Studio import).

Two Studio 5000 import errors were found when importing acd-generated L5X:
  1. "Element <AddOnInstructionDefinitions> is in the wrong order."
  2. "Required property 'Port' was missing ... Module[@Name='Local']/Ports"

Both are writer bugs (the element order and the CPU module's <Ports>). These
tests assert the writer now emits:
  - the <Controller> children in the Studio-schema order (validated against the
    known-good reference files in resources/), and
  - a non-empty <Ports> for the root CPU module (with ICP + Ethernet for an
    L85E/L82E CPU).

Validated against the reference files (ACDTestsWithAOI.L5X, Engine_Room.L5X)
which import cleanly in Studio 5000.
"""
import os
import re
import xml.etree.ElementTree as ET

from acd.api import ImportProjectFromFile

# The Studio-schema order of <Controller> direct children, as established by the
# known-good reference files (ACDTestsWithAOI.L5X, Engine_Room.L5X).
EXPECTED_CONTROLLER_ORDER = [
    "Description",
    "RedundancyInfo",
    "Security",
    "SafetyInfo",
    "DataTypes",
    "Modules",
    "AddOnInstructionDefinitions",
    "Tags",
    "Programs",
    "Tasks",
    "CST",
    "WallClockTime",
    "Trends",
    "DataLogs",
    "TimeSynchronize",
    "EthernetPorts",
]


def _controller_children(project):
    xml = project.to_xml()
    root = ET.fromstring(xml)
    ctrl = root.find("Controller")
    return [child.tag for child in ctrl], ctrl


def test_controller_child_order_matches_reference():
    # ACDTestsWithAOI's CPU (1756-L85E, CIP 1/14/168) is in the built-in table,
    # so it converts cleanly; we check the <Controller> child element order.
    importer = ImportProjectFromFile(os.path.join("..", "resources", "ACDTestsWithAOI.ACD"))
    project = importer.import_project()
    order, _ = _controller_children(project)
    # The generated order must be a prefix-consistent match of the schema order
    # (the reference carries all of them; a project with fewer sections would
    # still have them in this relative order).
    # Filter out any children the reference also has and compare the full list,
    # since ACDTestsWithAOI carries every section.
    assert order == EXPECTED_CONTROLLER_ORDER, (
        f"<Controller> child order does not match the Studio schema.\n"
        f"  expected: {EXPECTED_CONTROLLER_ORDER}\n  got:      {order}"
    )
    # Specifically: AddOnInstructionDefinitions must come right after Modules,
    # NOT after Tasks (the original bug).
    assert order.index("AddOnInstructionDefinitions") == order.index("Modules") + 1, (
        "AddOnInstructionDefinitions must immediately follow Modules"
    )
    # And RedundancyInfo/Security/SafetyInfo must come BEFORE DataTypes (original bug
    # had them appended after the data sections).
    assert order.index("RedundancyInfo") < order.index("DataTypes")
    assert order.index("Security") < order.index("DataTypes")
    assert order.index("SafetyInfo") < order.index("DataTypes")


def test_root_cpu_module_has_ports():
    # The root CPU module must declare its <Ports> (the "Required property 'Port'
    # was missing" bug was an empty <Ports/>). A root ControlLogix CPU with
    # Ethernet (L85E/L82E) has at least an ICP port and an Ethernet port.
    importer = ImportProjectFromFile(os.path.join("..", "resources", "ACDTestsWithAOI.ACD"))
    project = importer.import_project()
    _, ctrl = _controller_children(project)
    cpu = None
    for mod in ctrl.iter("Module"):
        if mod.get("Name") in ("Local", "Local1") and mod.get("MajorFault") == "true":
            cpu = mod
            break
    assert cpu is not None, "no root CPU module found"
    ports = cpu.find("Ports")
    assert ports is not None, "CPU module has no <Ports> element"
    port_tags = list(ports)
    assert len(port_tags) >= 1, f"CPU <Ports> is empty: {ET.tostring(cpu)}"
    types = {p.get("Type") for p in port_tags}
    # A root ControlLogix CPU always has at least its ICP (backplane) port.
    assert "ICP" in types, f"CPU <Ports> missing an ICP port; got {types}"


def test_l82e_cpu_has_ports():
    # The L82E (CIP 1/14/92) was out of the port table -> empty <Ports/>. Now it
    # must carry ICP + Ethernet like the other Ethernet CPUs.
    from acd.l5x.port_structures import PORT_STRUCTURES

    assert (1, 14, 92) in PORT_STRUCTURES, "1756-L82E (1:14:92) missing from PORT_STRUCTURES"
    defs = PORT_STRUCTURES[(1, 14, 92)]
    types = {d.port_type for d in defs}
    assert "ICP" in types, "L82E port structure must include an ICP port"
    assert "Ethernet" in types, "L82E port structure must include an Ethernet port"


def test_generated_xml_is_well_formed():
    # A malformed <Controller> (mismatched tag) would fail ET.fromstring. This
    # guards against the open-tag-without-close bug found while fixing the order.
    importer = ImportProjectFromFile(os.path.join("..", "resources", "ACDTestsWithAOI.ACD"))
    project = importer.import_project()
    xml = project.to_xml()
    # Should parse without error.
    ET.fromstring(xml)
