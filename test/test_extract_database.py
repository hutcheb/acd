import os
from pathlib import Path

from acd.api import ExtractAcdDatabaseRecordsToFiles


def test_dump_database():
    database = ExtractAcdDatabaseRecordsToFiles(Path(os.path.join("..", "resources", "CuteLogix.ACD")), Path(os.path.join("build")))
    database.extract()
