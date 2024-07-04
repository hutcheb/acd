import os
import sqlite3
import tempfile
from dataclasses import dataclass
from sqlite3 import Cursor, Connection

from loguru import logger as log

class DatabaseProvider:
    pass


@dataclass
class SqlDatabaseProvider(DatabaseProvider):
    directory: str = tempfile.mkdtemp()
    filename: str = "acd.db"
    _db: Connection = None
    _cur: Cursor = None

    def __post_init__(self):
        log.info("Creating temporary directory (if it doesn't exist to store ACD database files - " + self.directory)

        if os.path.exists(os.path.join(self.directory, self.filename)):
            os.remove(os.path.join(self.directory, self.filename))
        if not os.path.exists(os.path.join(self.directory)):
            os.makedirs(self.directory)
        log.info("Creating sqllite database to store ACD database records")
        self._db = sqlite3.connect(os.path.join(self.directory, self.filename))
        self._cur: Cursor = self._db.cursor()

        log.debug("Create Comps table in sqllite db")
        self._cur.execute("CREATE TABLE comps(object_id int, parent_id int, comp_name text, seq_number int, "
                          "record_type int, record BLOB NOT NULL)")

        log.debug("Create pointers table in sqllite db")
        self._cur.execute("CREATE TABLE pointers(object_id int, parent_id int, comp_name text, seq_number int, "
                          "record_type int, record BLOB NOT NULL)")

        log.debug("Create Rungs table in sqllite db")
        self._cur.execute("CREATE TABLE rungs(object_id int, rung text, seq_number int)")

        log.debug("Create Region_map table in sqllite db")
        self._cur.execute("CREATE TABLE region_map(object_id int, parent_id int, unknown int, seq_no int, record BLOB "
                          "NOT NULL)")
        log.debug("Create Comments table in sqllite db")
        self._cur.execute(
            "CREATE TABLE comments(seq_number int, string_length int, lookup_id int, comment text, record_type int, "
            "sub_record_type int)")

        log.debug("Create Nameless table in sqllite db")
        self._cur.execute(
            "CREATE TABLE nameless(object_id int, parent_id int, record BLOB NOT NULL)")