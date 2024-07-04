import argparse
import os
import sqlite3
import struct
import tempfile
from dataclasses import dataclass, field
from sqlite3 import Cursor

from acd.comments import CommentsRecord
from acd.comps import CompsRecord
from acd.dbextract import DbExtract
from acd.l5x.elements import Controller, ControllerBuilder
from acd.nameless import NamelessRecord
from acd.sbregion import SbRegionRecord
from acd.unzip import Unzip

from loguru import logger as log

@dataclass
class ExportL5x:
    input_filename: os.PathLike
    _temp_dir: str = "build" #tempfile.mkdtemp()
    _controller: Controller = None

    def __post_init__(self):
        log.info("Creating temporary directory (if it doesn't exist to store ACD database files - " + self._temp_dir)
        _DEFAULT_SQL_DATABASE_NAME = "acd.db"
        if os.path.exists(os.path.join(self._temp_dir, _DEFAULT_SQL_DATABASE_NAME)):
            os.remove(os.path.join(self._temp_dir, _DEFAULT_SQL_DATABASE_NAME))
        if not os.path.exists(os.path.join(self._temp_dir)):
            os.makedirs(self._temp_dir)
        log.info("Creating sqllite database to store ACD database records")
        self._db = sqlite3.connect(os.path.join(self._temp_dir, _DEFAULT_SQL_DATABASE_NAME))
        self._cur: Cursor = self._db.cursor()

        log.debug("Create Comps table in sqllite db")
        self._cur.execute("CREATE TABLE comps(object_id int, parent_id int, comp_name text, seq_number int, record_type int, record BLOB NOT NULL)")
        log.debug("Create pointers table in sqllite db")
        self._cur.execute("CREATE TABLE pointers(object_id int, parent_id int, comp_name text, seq_number int, record_type int, record BLOB NOT NULL)")
        log.debug("Create Rungs table in sqllite db")
        self._cur.execute("CREATE TABLE rungs(object_id int, rung text, seq_number int)")
        log.debug("Create Region_map table in sqllite db")
        self._cur.execute("CREATE TABLE region_map(object_id int, parent_id int, unknown int, seq_no int, record BLOB NOT NULL)")
        log.debug("Create Comments table in sqllite db")
        self._cur.execute(
            "CREATE TABLE comments(seq_number int, sub_record_length int, object_id int, record_string text, record_type int, parent int)")

        log.debug("Create Nameless table in sqllite db")
        self._cur.execute(
            "CREATE TABLE nameless(object_id int, parent_id int, record BLOB NOT NULL)")

        log.info("Extracting ACD database file")
        unzip = Unzip(self.input_filename)
        unzip.write_files(self._temp_dir)

        log.info("Getting records from ACD Comps file and storing in sqllite database")
        comps_db = DbExtract(os.path.join(self._temp_dir, "Comps.Dat")).read()
        for record in comps_db.records.record:
            CompsRecord(self._cur, record)
        self._db.commit()

        # Get a list of class ids for each collection
        # self._cur.execute("SELECT object_id, comp_name, record FROM comps WHERE parent_id=" + str(4240912631))
        # results = self._cur.fetchall()
        # classes = [[]]
        # for result in results:
        #     name = result[1]
        #     cip_class = hex(struct.unpack(
        #         "H", result[2][10: 10 + 2]
        #     )[0])
        #     classes.append([name, cip_class])


        log.info("Getting records from ACD Region Map file and storing in sqllite database")
        self.populate_region_map()

        log.info("Getting records from ACD SbRegion file and storing in sqllite database")
        sb_region_db = DbExtract(os.path.join(self._temp_dir, "SbRegion.Dat")).read()
        for record in sb_region_db.records.record:
            SbRegionRecord(self._cur, record)
        self._db.commit()

        log.info("Getting records from ACD Comments file and storing in sqllite database")
        comments_db = DbExtract(os.path.join(self._temp_dir, "Comments.Dat")).read()
        for record in comments_db.records.record:
            CommentsRecord(self._cur, record)
        self._db.commit()

        log.info("Getting records from ACD Nameless file and storing in sqllite database")
        nameless_db = DbExtract(os.path.join(self._temp_dir, "Nameless.Dat")).read()
        for record in nameless_db.records.record:
            NamelessRecord(self._cur, record)
        self._db.commit()

    @property
    def controller(self):
        if self._controller is None:
            self._controller = ControllerBuilder(self._cur).build()
        return self._controller


    def populate_region_map(self):
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE parent_id=0 AND comp_name='Region Map'")
        results = self._cur.fetchall()

        if len(results) == 0:
            return
        record = results[0][3]

        identifier_offset = 70

        if len(record) < (identifier_offset + 8):
            return

        region_length = struct.unpack(
            "I", record[identifier_offset + 4: identifier_offset + 8]
        )[0]

        identifier_offset = 78
        record_length_absolute = identifier_offset + region_length - 4
        c = 0
        while identifier_offset <= (record_length_absolute - 16):
            parent_id_identifier = struct.unpack(
                "I", record[identifier_offset: identifier_offset + 4]
            )[0]

            unknown_identifier = struct.unpack(
                "I", record[identifier_offset + 4: identifier_offset + 8]
            )[0]

            seq_identifier = struct.unpack(
                "I", record[identifier_offset + 8: identifier_offset + 12]
            )[0]

            c += 1
            object_id_identifier = struct.unpack(
                "I", record[identifier_offset + 12: identifier_offset + 16]
            )[0]

            query: str = "INSERT INTO region_map VALUES (?, ?, ?, ?, ?)"
            enty: tuple = (object_id_identifier, parent_id_identifier, unknown_identifier, seq_identifier, record[identifier_offset: identifier_offset + 16])
            self._cur.execute(query, enty)
            identifier_offset += 16

            self._db.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Read an ACD file and export the database as an L5X file')
    parser.add_argument('input', metavar='input', type=str, nargs='+',
                        help='The file to be converted')
    parser.add_argument('output', metavar='output', type=str, nargs='+',
                        help='Filename of the exported file')

    args = parser.parse_args()
    ExportL5x(args.input[0], args.output[0])