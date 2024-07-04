import os
from dataclasses import dataclass
from loguru import logger as log


from acd.dbextract import DbExtract
from acd.unzip import Unzip


@dataclass
class AcdDatabase:
    input_filename: os.PathLike
    output_filename: str
    _temp_dir: str = "build"  # tempfile.mkdtemp()

    def __post_init__(self):
        if not os.path.exists(os.path.join(self._temp_dir)):
            os.makedirs(self._temp_dir)

        log.info("Extracting ACD database file")
        unzip = Unzip(self.input_filename)
        unzip.write_files(self._temp_dir)

        log.info("Getting records from ACD Comps file and storing in sqllite database")
        self.comps_db = DbExtract(os.path.join(self._temp_dir, "Comps.Dat")).read()

        log.info("Getting records from ACD SbRegion file and storing in sqllite database")
        self.sb_region_db = DbExtract(os.path.join(self._temp_dir, "SbRegion.Dat")).read()

        log.info("Getting records from ACD Comments file and storing in sqllite database")
        self.comments_db = DbExtract(os.path.join(self._temp_dir, "Comments.Dat")).read()

        log.info("Getting records from ACD Nameless file and storing in sqllite database")
        self.nameless_db = DbExtract(os.path.join(self._temp_dir, "Nameless.Dat")).read()

    def extract_to_file(self):
        directory = os.path.join(self._temp_dir, "comps_db")
        if not os.path.exists(os.path.join(directory)):
            os.makedirs(directory)
        for count, record in enumerate(self.comps_db.records.record):
            with open(os.path.join(directory, str(count)), "wb") as out_file:
                out_file.write(record.record.record_buffer)

        directory = os.path.join(self._temp_dir, "sb_region_db")
        if not os.path.exists(os.path.join(directory)):
            os.makedirs(directory)
        for count, record in enumerate(self.sb_region_db.records.record):
            with open(os.path.join(directory, str(count)), "wb") as out_file:
                out_file.write(record.record.record_buffer)

        directory = os.path.join(self._temp_dir, "comments_db")
        if not os.path.exists(os.path.join(directory)):
            os.makedirs(directory)
        for count, record in enumerate(self.comments_db.records.record):
            with open(os.path.join(directory, str(count)), "wb") as out_file:
                out_file.write(record.record.record_buffer)

        directory = os.path.join(self._temp_dir, "nameless_db")
        if not os.path.exists(os.path.join(directory)):
            os.makedirs(directory)
        for count, record in enumerate(self.nameless_db.records.record):
            with open(os.path.join(directory, str(count)), "wb") as out_file:
                out_file.write(record.record.record_buffer)
