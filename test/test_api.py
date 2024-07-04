import os
from pathlib import Path

from acd.api import ImportProjectFromFile, Project, Extract, ExtractAcdDatabase
from acd.export_l5x import ExportL5x


from acd.l5x.elements import DumpCompsRecords


def test_import_from_file():
    importer = ImportProjectFromFile(Path(os.path.join("..", "resources", "CuteLogix.ACD")))
    project: Project = importer.import_project()
    assert project is not None


def test_extract_database_files():
    extractor: Extract = ExtractAcdDatabase(Path(os.path.join("..", "resources", "CuteLogix.ACD")), Path(os.path.join("build")))
    extractor.extract()


def test_dump_to_files():
    export = ExportL5x(Path(os.path.join("..", "resources", "CuteLogix.ACD")))
    DumpCompsRecords(export._cur, 0).dump(0)
