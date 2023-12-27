import struct
from dataclasses import dataclass
from sqlite3 import Cursor
from typing import List


@dataclass
class L5xElement:
    _cur: Cursor
    _object_id: int = -1


@dataclass
class DataType(L5xElement):

    def __post_init__(self):
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id=" + str(
                self._object_id))
        results = self._cur.fetchall()

        record = results[0][3]
        self.name = results[0][0]

        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE parent_id=" + str(
                self._object_id))
        member_results = self._cur.fetchall()
        if len(member_results) == 1:
            member_collection_id = member_results[0][1]

            self._cur.execute(
                "SELECT comp_name, object_id, parent_id, record FROM comps WHERE parent_id=" + str(
                    member_collection_id))
            children_results = self._cur.fetchall()
            self.children = []
            for child in children_results:
                self.children.append(child[0])


@dataclass
class Tag(L5xElement):

    def __post_init__(self):
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id=" + str(
                self._object_id))
        results = self._cur.fetchall()

        record = results[0][3]
        self.text = results[0][0]

        hidden_offset = 8
        self.hidden = struct.unpack(
            "H", record[hidden_offset: hidden_offset + 2]
        )[0] == 256

        one_dim_array_length_offest = 174
        self.one_dim_array_length = struct.unpack(
            "I", record[one_dim_array_length_offest: one_dim_array_length_offest + 4]
        )[0]

        two_dim_array_length_offest = 178
        self.two_dim_array_length = struct.unpack(
            "I", record[two_dim_array_length_offest: two_dim_array_length_offest + 4]
        )[0]

        three_dim_array_length_offest = 182
        self.three_dim_array_length = struct.unpack(
            "I", record[three_dim_array_length_offest: three_dim_array_length_offest + 4]
        )[0]

        data_type_offest = 190
        data_type_id = struct.unpack(
            "I", record[data_type_offest: data_type_offest + 4]
        )[0]

        if data_type_id == 4294967295:
            self.data_type = ""
        else:
            self._cur.execute(
                "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id=" + str(
                    data_type_id))
            data_type_results = self._cur.fetchall()

            self.data_type = data_type_results[0][0]

        if  self.one_dim_array_length != 0:
            self.data_type = self.data_type + "[" + str(self.one_dim_array_length) + "]"
        if  self.two_dim_array_length != 0:
            self.data_type = self.data_type + "[" + str(self.two_dim_array_length) + "]"
        if  self.three_dim_array_length != 0:
            self.data_type = self.data_type + "[" + str(self.three_dim_array_length) + "]"




@dataclass
class Routine(L5xElement):

    def __post_init__(self):
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id=" + str(
                self._object_id))
        results = self._cur.fetchall()

        record = results[0][3]
        self.name = results[0][0]

        self._cur.execute(
            "SELECT object_id, parent_id, seq_no FROM region_map WHERE parent_id=" + str(
                self._object_id) +  " ORDER BY seq_no")
        results = self._cur.fetchall()
        self.rungs = []
        for member in results:
            self._cur.execute(
                "SELECT object_id, rung FROM rungs WHERE object_id=" + str(
                    member[0]))
            rungs_results = self._cur.fetchall()
            if len(rungs_results) > 0:
                self.rungs.append(rungs_results[0][1])
        pass

@dataclass
class AOI(L5xElement):

    def __post_init__(self):
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id=" + str(
                self._object_id))
        results = self._cur.fetchall()

        record = results[0][3]
        self.name = results[0][0]

        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE parent_id=" + str(
                self._object_id) + " AND comp_name='RxRoutineCollection'")
        collection_results = self._cur.fetchall()
        collection_id = collection_results[0][1]

        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE parent_id=" + str(
                collection_id))
        routine_results = self._cur.fetchall()

        self.routines = []
        for child in routine_results:
            self.routines.append(Routine(self._cur, child[1]))

        # Get the Program Scoped Tags
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id=" + str(
                self._object_id) + " AND comp_name='RxTagCollection'")
        results = self._cur.fetchall()
        if len(results) > 1:
            raise Exception("Contains more than one program tag collection")

        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id=" + str(
                results[0][1]))
        results = self._cur.fetchall()
        self.tags: List[Tag] = []
        for result in results:
            self.tags.append(Tag(self._cur, result[1]))


@dataclass
class Program(L5xElement):

    def __post_init__(self):
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id=" + str(
                self._object_id))
        results = self._cur.fetchall()

        record = results[0][3]
        self.name = results[0][0]

        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE parent_id=" + str(
                self._object_id) + " AND comp_name='RxRoutineCollection'")
        collection_results = self._cur.fetchall()
        collection_id = collection_results[0][1]

        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE parent_id=" + str(
                collection_id))
        routine_results = self._cur.fetchall()

        self.routines = []
        for child in routine_results:
            self.routines.append(Routine(self._cur, child[1]))

        # Get the Program Scoped Tags
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id=" + str(
                self._object_id) + " AND comp_name='RxTagCollection'")
        results = self._cur.fetchall()
        if len(results) > 1:
            raise Exception("Contains more than one program tag collection")

        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id=" + str(
                results[0][1]))
        results = self._cur.fetchall()
        self.tags: List[Tag] = []
        for result in results:
            self.tags.append(Tag(self._cur, result[1]))


@dataclass
class Controller(L5xElement):
    controller_name: str = ""

    def __post_init__(self):
        self._cur.execute("SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id=0 AND record_type=256")
        results = self._cur.fetchall()
        if len(results) != 1:
            raise Exception("Does not contain exactly one root controller node")

        self._object_id = results[0][1]
        self.controller_name = results[0][0]

        # Get the data types
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id=" + str(
                self._object_id) + " AND comp_name='RxDataTypeCollection'")
        results = self._cur.fetchall()
        if len(results) > 1:
            raise Exception("Contains more than one controller data type collection")

        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id=" + str(
                results[0][1]))
        results = self._cur.fetchall()
        self.data_types: List[DataType] = []
        for result in results:
            self.data_types.append(DataType(self._cur, result[1]))

        # Get the Controller Scoped Tags
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id=" +  str(self._object_id) + " AND comp_name='RxTagCollection'")
        results = self._cur.fetchall()
        if len(results) > 1:
            raise Exception("Contains more than one controller tag collection")

        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id=" + str(
                results[0][1]))
        results = self._cur.fetchall()
        self.tags: List[Tag] = []
        for result in results:
            self.tags.append(Tag(self._cur, result[1]))

        # Get the Program Collection and get the programs
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id=" + str(
                self._object_id) + " AND comp_name='RxProgramCollection'")
        results = self._cur.fetchall()
        if len(results) > 1:
            raise Exception("Contains more than one controller program collection")

        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id=" + str(
                results[0][1]))
        results = self._cur.fetchall()
        self.programs: List[Program] = []
        for result in results:
            self.programs.append(Program(self._cur, result[1]))

        # Get the AOI Collection and get the AOIs
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id=" + str(
                self._object_id) + " AND comp_name='RxUDIDefinitionCollection'")
        results = self._cur.fetchall()
        if len(results) > 1:
            raise Exception("Contains more than one AOI collection")

        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id=" + str(
                results[0][1]))
        results = self._cur.fetchall()
        self.aois: List[Program] = []
        for result in results:
            self.aois.append(AOI(self._cur, result[1]))
