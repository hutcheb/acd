import os
import xml.etree.ElementTree as ET

import pytest

from acd.api import ImportProjectFromFile
from acd.l5x.elements import radix_enum

RESOURCES = os.path.join("..", "resources")


@pytest.mark.parametrize(
    "value, expected",
    [
        (4, "Decimal"),
        (11, "Date/Time (ns)"),
        (12, "Time32 (us)"),
        (13, "Time (us)"),
        (14, "LTime (ns)"),
    ],
)
def test_radix_enum(value, expected):
    assert radix_enum(value) == expected


def _controller_tag_radixes(root):
    tags = root.find("Controller").find("Tags")
    return {tag.get("Name"): tag.get("Radix") for tag in tags}


def test_controller_tag_radixes_match_reference_l5x():
    # ACDTestsWithAOI.L5X was exported by Studio 5000 from the same project,
    # including one tag per radix (TIME, TIME32 and LTIME among them).
    project = ImportProjectFromFile(os.path.join(RESOURCES, "ACDTestsWithAOI.ACD")).import_project()
    generated = _controller_tag_radixes(ET.fromstring(project.to_xml()))
    reference = _controller_tag_radixes(ET.parse(os.path.join(RESOURCES, "ACDTestsWithAOI.L5X")).getroot())

    mismatches = {
        name: (radix, generated[name])
        for name, radix in reference.items()
        if radix is not None and name in generated and generated[name] != radix
    }
    assert mismatches == {}
