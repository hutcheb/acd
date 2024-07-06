import os
import shutil
import struct
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from sqlite3 import Cursor
from typing import List, Tuple, Dict

from acd.exceptions.CompsRecordException import UnknownRxTagVersion
from acd.generated.comps.rx_tag import RxTag
from acd.generated.controller.rx_controller import RxController
from acd.generated.map_device.rx_map_device import RxMapDevice


@dataclass
class L5xElementBuilder:
    _cur: Cursor
    _object_id: int = -1


@dataclass
class L5xElement:
    name: str


@dataclass
class DataType(L5xElement):
    children: List[str]


@dataclass
class Tag(L5xElement):
    data_table_instance: int
    data_type: str
    comments: List[Tuple[str, str]]


@dataclass
class MapDevice(L5xElement):
    module_id: int
    parent_module: int
    slot_no: int
    vendor_id: int
    product_type: int
    product_code: int
    comments: List[Tuple[str, str]]


@dataclass
class Routine(L5xElement):
    rungs: List[str]


@dataclass
class AOI(L5xElement):
    routines: List[Routine]
    tags: List[Tag]


@dataclass
class Program(L5xElement):
    routines: List[Routine]
    tags: List[Tag]


@dataclass
class Controller(L5xElement):
    serial_number: str
    path: str
    data_types: List[DataType]
    tags: List[Tag]
    programs: List[Program]
    aois: List[AOI]
    map_devices: List[MapDevice]


@dataclass
class DataTypeBuilder(L5xElementBuilder):

    def build(self) -> DataType:
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id=" + str(
                self._object_id))
        results = self._cur.fetchall()

        record = results[0][3]
        name = results[0][0]

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
            children = []
            for child in children_results:
                children.append(child[0])
            return DataType(name, children)
        return DataType(name, [])


@dataclass
class MapDeviceBuilder(L5xElementBuilder):

    def build(self) -> MapDevice:
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id=" + str(
                self._object_id))
        results = self._cur.fetchall()

        r = RxMapDevice.from_bytes(results[0][3])

        if r.record_format_version == 0x00:
            return MapDevice(results[0][0], 0, 0, 0, 0, 0, [])
        elif not r.body.valid:
            return MapDevice("", 0, 0, 0, 0, 0, [])

        self._cur.execute(
            "SELECT tag_reference, record_string FROM comments WHERE parent=" + str(
                r.comment_id))
        comment_results = self._cur.fetchall()

        name = results[0][0]
        return MapDevice(name, r.body.module_id, r.body.parent_module, r.body.slot_no, r.body.vendor_id, r.body.product_type, r.body.product_code, comment_results)


@dataclass
class TagBuilder(L5xElementBuilder):

    def build(self) -> Tag:
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id=" + str(
                self._object_id))
        results = self._cur.fetchall()

        r = RxTag.from_bytes(results[0][3])

        if r.record_format_version == 0x00:
            return Tag(results[0][0], 0, "", [])
        elif not r.body.valid:
            raise UnknownRxTagVersion(r.record_format_version)

        if r.body.data_type == 4294967295:
            data_type = ""
            name = r.body.name
            comment_results = []
        else:
            self._cur.execute(
                "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id=" + str(
                    r.body.data_type))
            data_type_results = self._cur.fetchall()
            data_type = data_type_results[0][0]

            self._cur.execute(
                "SELECT tag_reference, record_string FROM comments WHERE parent=" + str(
                    r.comment_id))
            comment_results = self._cur.fetchall()
            try:
                name = r.body.name
            except Exception as e:
                name = ""
            if len(comment_results) > 0:
                pass
        if r.body.dimension_1 != 0:
            data_type = data_type + "[" + str(r.body.dimension_1) + "]"
        if r.body.dimension_2 != 0:
            data_type = data_type + "[" + str(r.body.dimension_2) + "]"
        if r.body.dimension_3 != 0:
            data_type = data_type + "[" + str(r.body.dimension_3) + "]"
        return Tag(name, r.body.data_table_instance, data_type, comment_results)


@dataclass
class RoutineBuilder(L5xElementBuilder):

    def build(self) -> Routine:
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id=" + str(
                self._object_id))
        results = self._cur.fetchall()

        record = results[0][3]
        name = results[0][0]

        self._cur.execute(
            "SELECT object_id, parent_id, seq_no FROM region_map WHERE parent_id=" + str(
                self._object_id) +  " ORDER BY seq_no")
        results = self._cur.fetchall()
        rungs = []
        for member in results:
            self._cur.execute(
                "SELECT object_id, rung FROM rungs WHERE object_id=" + str(
                    member[0]))
            rungs_results = self._cur.fetchall()
            if len(rungs_results) > 0:
                rungs.append(rungs_results[0][1])
        return Routine(name, rungs)


@dataclass
class AoiBuilder(L5xElementBuilder):

    def build(self) -> AOI:
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id=" + str(
                self._object_id))
        results = self._cur.fetchall()

        record = results[0][3]
        name = results[0][0]

        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE parent_id=" + str(
                self._object_id) + " AND comp_name='RxRoutineCollection'")
        collection_results = self._cur.fetchall()
        if len(collection_results) != 0:
            collection_id = collection_results[0][1]
        else:
            routines = []
            tags: List[Tag] = []
            return AOI(name, routines, tags)

        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE parent_id=" + str(
                collection_id))
        routine_results = self._cur.fetchall()

        routines = []
        for child in routine_results:
            routines.append(RoutineBuilder(self._cur, child[1]).build())

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
        tags: List[Tag] = []
        for result in results:
            tags.append(TagBuilder(self._cur, result[1]).build())

        return AOI(name, routines, tags)


@dataclass
class ProgramBuilder(L5xElementBuilder):

    def build(self) -> Program:
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id=" + str(
                self._object_id))
        results = self._cur.fetchall()

        name = results[0][0]

        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE parent_id=" + str(
                self._object_id) + " AND comp_name='RxRoutineCollection'")
        collection_results = self._cur.fetchall()
        collection_id = collection_results[0][1]

        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE parent_id=" + str(
                collection_id))
        routine_results = self._cur.fetchall()

        routines = []
        for child in routine_results:
            routines.append(RoutineBuilder(self._cur, child[1]).build())

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
        tags: List[Tag] = []
        for result in results:
            tags.append(TagBuilder(self._cur, result[1]).build())

        return Program(name, routines, tags)


@dataclass
class ControllerBuilder(L5xElementBuilder):

    def build(self) -> Controller:
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type, record FROM comps WHERE parent_id=0 AND record_type=256")
        results = self._cur.fetchall()
        if len(results) != 1:
            raise Exception("Does not contain exactly one root controller node")
        serial_number = ""
        path = ""
        try:
            r = RxController.from_bytes(results[0][4])
            serial_number = hex(r.body.serial_number)
            if r.record_format_version == 103:
                path = r.body.path
        except:
            pass

        self._object_id = results[0][1]
        controller_name = results[0][0]

        # Get the data types
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id=" + str(
                self._object_id) + " AND comp_name='RxDataTypeCollection'")
        results = self._cur.fetchall()
        if len(results) > 1:
            raise Exception("Contains more than one controller data type collection")

        _data_type_id = results[0][1]
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id=" + str(
                _data_type_id))
        results = self._cur.fetchall()

        data_types: List[DataType] = []
        for result in results:
            _data_type_object_id = result[1]
            data_types.append(DataTypeBuilder(self._cur, _data_type_object_id).build())

        # Get the Controller Scoped Tags
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id=" + str(
                self._object_id) + " AND comp_name='RxTagCollection'")
        results = self._cur.fetchall()
        if len(results) > 1:
            raise Exception("Contains more than one controller tag collection")
        _tag_collection_object_id = results[0][1]
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id=" + str(
                _tag_collection_object_id))
        results = self._cur.fetchall()
        tags: List[Tag] = []
        for result in results:
            _tag_object_id = result[1]
            tags.append(TagBuilder(self._cur, _tag_object_id).build())

        # Get the Program Collection and get the programs
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id=" + str(
                self._object_id) + " AND comp_name='RxProgramCollection'")
        results = self._cur.fetchall()
        if len(results) > 1:
            raise Exception("Contains more than one controller program collection")

        _program_collection_object_id = results[0][1]
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id=" + str(
                _program_collection_object_id))
        results = self._cur.fetchall()
        programs: List[Program] = []
        for result in results:
            _program_object_id = result[1]
            programs.append(ProgramBuilder(self._cur, _program_object_id).build())

        # Get the AOI Collection and get the AOIs
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id=" + str(
                self._object_id) + " AND comp_name='RxUDIDefinitionCollection'")
        results = self._cur.fetchall()
        if len(results) > 1:
            raise Exception("Contains more than one AOI collection")
        _aoi_collection_object_id = results[0][1]
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id=" + str(
                _aoi_collection_object_id))
        results = self._cur.fetchall()
        aois: List[AOI] = []
        for result in results:
            _aoi_object_id = result[1]
            aois.append(AoiBuilder(self._cur, _aoi_object_id).build())

        # Get the Map Device (IO) Collection and get the MapDevices
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id=" + str(
                self._object_id) + " AND comp_name='RxMapDeviceCollection'")
        results = self._cur.fetchall()
        if len(results) > 1:
            raise Exception("Contains more than one Map Device collection")
        _map_device_collection_object_id = results[0][1]
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id=" + str(
                _map_device_collection_object_id))
        results = self._cur.fetchall()
        map_devices: List[MapDevice] = []
        for result in results:
            _map_device_object_id = result[1]
            map_devices.append(MapDeviceBuilder(self._cur, _map_device_object_id).build())

        return Controller(controller_name, serial_number, path, data_types, tags, programs, aois, map_devices)

@dataclass
class DumpCompsRecords(L5xElementBuilder):
    base_directory: PathLike = Path("dump")

    def dump(self, parent_id: int = 0):
        self._cur.execute(
            f"SELECT comp_name, object_id, parent_id, record_type, record FROM comps WHERE parent_id={parent_id}")
        results = self._cur.fetchall()

        for result in results:
            object_id = result[1]
            name = result[0]
            record = result[4]
            new_path = Path(os.path.join(self.base_directory, name))
            if os.path.exists(os.path.join(new_path)):
                shutil.rmtree(os.path.join(new_path))
            if not os.path.exists(os.path.join(new_path)):
                os.makedirs(new_path)
            with open(Path(os.path.join(new_path, name + ".dat")), "wb") as file:
                file.write(record)

            DumpCompsRecords(self._cur, object_id, new_path).dump(object_id)


