import argparse
import os
import re
import sqlite3
import struct
import tempfile
from dataclasses import dataclass
from sqlite3 import Cursor

from acd.comps import CompsRecord
from acd.dbextract import DbExtract
from acd.l5x.elements import Controller
from acd.sbregion import SbRegionRecord
from acd.unzip import Unzip


@dataclass
class ExportL5x:
    input_filename: str
    output_filename: str

    def __post_init__(self):
        self._temp_dir = tempfile.mkdtemp()
        os.remove("acd.db")
        self._db = sqlite3.connect(os.path.join("acd.db"))
        self._cur: Cursor = self._db.cursor()
        self._cur.execute("CREATE TABLE comps(object_id int, parent_id int, comp_name text, seq_number int, record_type int, record BLOB NOT NULL)")
        self._cur.execute("CREATE TABLE pointers(object_id int, parent_id int, comp_name text, seq_number int, record_type int, record BLOB NOT NULL)")
        self._cur.execute("CREATE TABLE rungs(object_id int, rung text, seq_number int)")
        self._cur.execute("CREATE TABLE region_map(object_id int, parent_id int)")
        unzip = Unzip(self.input_filename)
        unzip.write_files(self._temp_dir)
        comps_db = DbExtract(os.path.join(self._temp_dir, "Comps.Dat"))

        for record in comps_db.records:
            CompsRecord(self._cur, record)
            self._db.commit()

        self.populate_region_map()

        sb_region_db = DbExtract(os.path.join(self._temp_dir, "SbRegion.Dat"))
        for record in sb_region_db.records:
            SbRegionRecord(self._cur, record)
            self._db.commit()

        self.controller = Controller(self._cur)


    def populate_region_map(self):
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE parent_id=0 AND comp_name='Region Map'")
        results = self._cur.fetchall()

        record = results[0][3]

        identifier_offset = 218
        record_identifier = struct.unpack(
            "I", record[identifier_offset: identifier_offset + 4]
        )[0]

        while record_identifier == 4294967295:
            record_identifier = struct.unpack(
                "I", record[identifier_offset: identifier_offset + 4]
            )[0]

            object_id_identifier = struct.unpack(
                "I", record[identifier_offset + 4: identifier_offset + 8]
            )[0]

            parent_id_identifier = struct.unpack(
                "I", record[identifier_offset + 8: identifier_offset + 12]
            )[0]

            identifier_offset += 16

            if record_identifier == 4294967295:
                query: str = "INSERT INTO region_map VALUES (?, ?)"
                enty: tuple = (object_id_identifier, parent_id_identifier)
                self._cur.execute(query, enty)

        self._db.commit()

        pass





if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Read an ACD file and export the database as an L5X file')
    parser.add_argument('input', metavar='input', type=str, nargs='+',
                        help='The file to be converted')
    parser.add_argument('output', metavar='output', type=str, nargs='+',
                        help='Filename of the exported file')

    args = parser.parse_args()
    ExportL5x(args.input[0], args.output[0])