from acd import ImportProjectFromFile, Project, Extract, ExtractAcdDatabase


def test_import_from_file():
    importer = ImportProjectFromFile("../resources/CuteLogix.ACD")
    project: Project = importer.import_project()
    assert project is not None


def test_extract_databasee_files():
    extractor: Extract = ExtractAcdDatabase("../resources/CuteLogix.ACD", "build")
    extractor.extract()
