import os
from pathlib import Path

from acd import ImportProjectFromFile, Project, Extract, ExtractAcdDatabase


def test_import_from_file():
    importer = ImportProjectFromFile(Path(os.path.join("..", "resources", "CuteLogix.ACD")))
    project: Project = importer.import_project()
    assert project is not None


def test_extract_database_files():
    extractor: Extract = ExtractAcdDatabase(Path(os.path.join("..", "resources", "CuteLogix.ACD")), Path(os.path.join("build")))
    extractor.extract()
