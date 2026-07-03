import os
from pathlib import Path
from xml.dom import minidom

from acd.api import (
    ImportProjectFromFile,
    RSLogix5000Content,
    Extract,
    ExtractAcdDatabase,
    DumpCompsRecordsToFile,
)


def test_import_from_file():
    importer = ImportProjectFromFile(
        Path(os.path.join("..", "resources", "CuteLogix.ACD"))
    )
    project: RSLogix5000Content = importer.import_project()
    assert project is not None


def test_extract_database_files():
    extractor: Extract = ExtractAcdDatabase(
        Path(os.path.join("..", "resources", "CuteLogix.ACD")),
        Path(os.path.join("build")),
    )
    extractor.extract()


def test_dump_to_files():
    DumpCompsRecordsToFile(
        os.path.join("..", "resources", "CuteLogix.ACD"), "build"
    ).extract()


def test_to_xml():
    importer = ImportProjectFromFile(
        Path(os.path.join("..", "resources", "CuteLogix.ACD"))
    )
    project: RSLogix5000Content = importer.import_project()
    unformatted_string = project.to_xml()
    xmlstr = minidom.parseString(unformatted_string).toprettyxml(indent="   ")
    with open(os.path.join("build", "CuteLogix.L5X"), "w") as out_file:
        out_file.write(xmlstr)


def test_st_routine_content():
    """ST routine bodies are extracted from the nameless records: source
    lines in order, blank lines preserved, @hexid@ tag references resolved,
    and exported as an L5X STContent element."""
    importer = ImportProjectFromFile(
        Path(os.path.join("..", "resources", "ACDTestsNonRedundant.ACD"))
    )
    project: RSLogix5000Content = importer.import_project()
    st_routines = [
        rt
        for prog in project.controller.programs
        for rt in prog.routines
        if rt.type == "ST"
    ]
    assert st_routines, "fixture should contain an ST routine"
    st = st_routines[0]
    assert st._st_lines, "ST routine should have extracted source lines"
    body = "\n".join(st._st_lines)
    assert ":=" in body
    assert "@" not in body, "tag references should be resolved to names"
    xml = st.to_xml()
    assert "<STContent>" in xml
    assert '<Line Number="0"><![CDATA[' in xml
    # Line numbering must match source positions (blank lines preserved)
    assert f'<Line Number="{len(st._st_lines) - 1}">' in xml
