import os
import xml.etree.ElementTree as ET

from acd.api import ImportProjectFromFile
from acd.l5x.export_l5x import ExportL5x
from acd.l5x.st_decoder import STDecoder

AOI_ACD = os.path.join("..", "resources", "ACDTestsWithAOI.ACD")
AOI_L5X = os.path.join("..", "resources", "ACDTestsWithAOI.L5X")


def _controller(xml: str):
    return ET.fromstring(xml).find("Controller")


def test_st_routine_lines_match_reference_export():
    def st_lines(controller):
        routine = next(r for r in controller.iter("Routine") if r.get("Name") == "STRoutine")
        assert routine.get("Type") == "ST"
        # Rockwell's export puts a newline either side of each CDATA section;
        # strip that framing so only the source text is compared.
        return [(line.text or "").strip("\n") for line in routine.find("STContent").findall("Line")]

    project = ImportProjectFromFile(AOI_ACD).import_project()
    expected = st_lines(ET.parse(AOI_L5X).getroot().find("Controller"))
    assert len(expected) == 6
    assert st_lines(_controller(project.to_xml())) == expected


def _st_warnings(monkeypatch, all_routines):
    from loguru import logger

    monkeypatch.setattr(STDecoder, "all_routines", all_routines)
    warnings = []
    sink = logger.add(lambda message: warnings.append(str(message)), level="WARNING")
    try:
        ImportProjectFromFile(AOI_ACD).import_project()
    finally:
        logger.remove(sink)
    return [w for w in warnings if "Structured Text" in w]


def test_st_decoding_failure_warns_once_plus_once_per_routine(monkeypatch):
    def fail(self):
        raise ValueError("bad index")

    warnings = _st_warnings(monkeypatch, fail)
    assert len(warnings) == 2
    assert (
        "Structured Text routine bodies could not be decoded; ST routines were "
        "exported with no lines (bad index)" in warnings[0]
    )
    assert "Structured Text routines with no decoded lines, exported empty: STRoutine" in warnings[1]


def test_st_routine_without_lines_warns(monkeypatch):
    warnings = _st_warnings(monkeypatch, lambda self: [])
    assert len(warnings) == 1
    assert "Structured Text routines with no decoded lines, exported empty: STRoutine" in warnings[0]


def test_st_decoding_failure_is_recorded_in_project_notes(monkeypatch):
    def fail(self):
        raise ValueError("bad index")

    monkeypatch.setattr(STDecoder, "all_routines", fail)
    project = ExportL5x(AOI_ACD).project

    assert project.conversion_notes == [
        "Structured Text routine bodies could not be decoded; "
        "ST routines were exported with no lines",
        "Structured Text routines with no decoded lines, exported empty: 'STRoutine'",
    ]


def test_st_routine_without_lines_is_recorded_in_project_notes(monkeypatch):
    monkeypatch.setattr(STDecoder, "all_routines", lambda self: [])
    project = ExportL5x(AOI_ACD).project

    assert project.conversion_notes == [
        "Structured Text routines with no decoded lines, exported empty: 'STRoutine'",
    ]
