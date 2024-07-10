import os
from pathlib import Path

from acd.api import ImportProjectFromFile, RSLogix5000Content, Extract, ExtractAcdDatabase, DumpCompsRecordsToFile
from acd.export_l5x import ExportL5x


from acd.l5x.elements import DumpCompsRecords
from xml.dom import minidom



def test_import_from_file():
    importer = ImportProjectFromFile(Path(os.path.join("..", "resources", "CuteLogix.ACD")))
    project: RSLogix5000Content = importer.import_project()
    assert project is not None


def test_extract_database_files():
    extractor: Extract = ExtractAcdDatabase(Path(os.path.join("..", "resources", "CuteLogix.ACD")), Path(os.path.join("build")))
    extractor.extract()


def test_dump_to_files():
    DumpCompsRecordsToFile(os.path.join("..", "resources", "CuteLogix.ACD"), 'build').extract()


def test_to_xml():
    importer = ImportProjectFromFile(Path(os.path.join("..", "resources", "CuteLogix.ACD")))
    project: RSLogix5000Content = importer.import_project()
    unformatted_string = project.to_xml()
    xmlstr = minidom.parseString(unformatted_string).toprettyxml(indent="   ")
    with open(os.path.join("build", "CuteLogix.L5X"), "w") as out_file:
        out_file.write(xmlstr)
