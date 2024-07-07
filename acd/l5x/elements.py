import os
import shutil
import struct
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from sqlite3 import Cursor
from typing import List, Tuple, Dict
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

from acd.exceptions.CompsRecordException import UnknownRxTagVersion
from acd.generated.comps.rx_generic import RxGeneric
from acd.generated.comps.rx_tag import RxTag
from acd.generated.controller.rx_controller import RxController
from acd.generated.map_device.rx_map_device import RxMapDevice


@dataclass
class L5xElementBuilder:
    _cur: Cursor
    _object_id: int = -1


@dataclass
class L5xElement:
    _name: str

    def __post_init__(self):
        self._export_name = ""

    def to_xml(self):
        attribute_list: List[str] = []
        child_list: List[str] = []
        for attribute in self.__dict__:
            if attribute[0] != "_":
                attribute_value = self.__getattribute__(attribute)
                if isinstance(attribute_value, L5xElement):
                    child_list.append(attribute_value.to_xml())
                elif isinstance(attribute_value, list):
                    if attribute == "tags":
                        new_child_list: List[str] = []
                        for element in attribute_value:
                            if isinstance(element, L5xElement):
                                new_child_list.append(element.to_xml())
                            else:
                                new_child_list.append(f"<{element}/>")
                        child_list.append(f'<{attribute.title().replace("_", "")}>{" ".join(new_child_list)}</{attribute.title().replace("_", "")}>')

                else:
                    attribute_list.append(f'{attribute.title().replace("_", "")}="{attribute_value}"')

        _export_name = self.__class__.__name__.title().replace("_", "")
        return f'<{_export_name} {" ".join(attribute_list)}>{" ".join(child_list)}</{_export_name}>'


@dataclass
class DataType(L5xElement):
    name: str
    children: List[str]


@dataclass
class Tag(L5xElement):
    name: str
    tag_type: str
    data_type: str
    radix: str
    external_access: str
    _data_table_instance: int
    _comments: List[Tuple[str, str]]


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
    sfc_execution_control: str
    sfc_restart_position: str
    sfc_last_scan: str
    created_date: str
    modified_date: str
    data_types: List[DataType]
    tags: List[Tag]
    programs: List[Program]
    aois: List[AOI]
    map_devices: List[MapDevice]


@dataclass
class RSLogix5000Content(L5xElement):
    """Controller Project"""
    controller: Controller
    schema_revision: str
    software_revision: str
    target_name: str
    target_name: str
    contains_context: str
    export_date: str
    export_options: str

    def __post_init__(self):
        self._name = "RSLogix5000Content"


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
            return DataType(name, name, children)
        return DataType(name, name, [])


@dataclass
class MapDeviceBuilder(L5xElementBuilder):

    def build(self) -> MapDevice:
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id=" + str(
                self._object_id))
        results = self._cur.fetchall()
        try:
            r = RxGeneric.from_bytes(results[0][3])
        except Exception as e:
            return MapDevice(results[0][0], 0, 0, 0, 0, 0, 0, [])

        if r.cip_type != 0x69:
            return MapDevice(results[0][0], 0, 0, 0, 0, 0, 0, [])

        self._cur.execute(
            "SELECT tag_reference, record_string FROM comments WHERE parent=" + str(
                (r.comment_id * 0x10000) + r.cip_type))
        comment_results = self._cur.fetchall()

        extended_records: Dict[int, List[int]] = {}
        for extended_record in r.extended_records:
            extended_records[extended_record.attribute_id] = extended_record.value
        extended_records[r.last_extended_record.attribute_id] = r.last_extended_record.value

        vendor_id = struct.unpack("<H", extended_records[0x01][2:4])[0]
        product_type = struct.unpack("<H", extended_records[0x01][4:6])[0]
        product_code = struct.unpack("<H", extended_records[0x01][6:8])[0]
        parent_module = struct.unpack("<I", extended_records[0x01][0x16:0x1A])[0]
        slot_no = struct.unpack("<I", extended_records[0x01][0x1C:0x20])[0]
        module_id = struct.unpack("<I", extended_records[0x01][0x2C:0x30])[0]
        name = results[0][0]

        return MapDevice(name, module_id, parent_module, slot_no, vendor_id, product_type, product_code, comment_results)


@dataclass
class TagBuilder(L5xElementBuilder):

    def build(self) -> Tag:
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id=" + str(
                self._object_id))
        results = self._cur.fetchall()

        try:
            r = RxGeneric.from_bytes(results[0][3])
        except Exception as e:
            return Tag(results[0][0], results[0][0], "Base", "", "Decimal", "None", 0, [])

        if r.cip_type != 0x6B:
            return Tag(results[0][0], results[0][0], "Base", "", "Decimal", "None", 0, [])
        if r.main_record.data_type == 0xFFFFFFFF:
            return Tag(results[0][0], results[0][0], "Base", "", "Decimal", "None", r.main_record.data_table_instance, [])

        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id=" + str(
                r.main_record.data_type))
        data_type_results = self._cur.fetchall()
        data_type = data_type_results[0][0]

        self._cur.execute(
            "SELECT tag_reference, record_string FROM comments WHERE parent=" + str(
                (r.comment_id * 0x10000) + r.cip_type))
        comment_results = self._cur.fetchall()

        extended_records: Dict[int, List[int]] = {}
        for extended_record in r.extended_records:
            extended_records[extended_record.attribute_id] = extended_record.value
        extended_records[r.last_extended_record.attribute_id] = r.last_extended_record.value

        name_length = struct.unpack("<H", extended_records[0x01][0:2])[0]
        name = bytes(extended_records[0x01][2:name_length+2]).decode('utf-8')

        if r.main_record.dimension_1 != 0:
            data_type = data_type + "[" + str(r.main_record.dimension_1) + "]"
        if r.main_record.dimension_2 != 0:
            data_type = data_type + "[" + str(r.main_record.dimension_2) + "]"
        if r.main_record.dimension_3 != 0:
            data_type = data_type + "[" + str(r.main_record.dimension_3) + "]"
        return Tag(name, name, "Base",  data_type, "Decimal", "Read/Write", r.main_record.data_table_instance, comment_results)


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

        r = RxGeneric.from_bytes(results[0][4])
        self._cur.execute(
            "SELECT tag_reference, record_string FROM comments WHERE parent=" + str(
                (r.comment_id * 0x10000) + r.cip_type))
        comment_results = self._cur.fetchall()

        extended_records: Dict[int, List[int]] = {}
        for extended_record in r.extended_records:
            extended_records[extended_record.attribute_id] = extended_record.value
        extended_records[r.last_extended_record.attribute_id] = r.last_extended_record.value

        path = bytes(extended_records[0x6a][:-2]).decode('utf-16')
        sfc_execution_control = bytes(extended_records[0x6F][:-2]).decode('utf-16')
        sfc_restart_position = bytes(extended_records[0x70][:-2]).decode('utf-16')
        sfc_last_scan = bytes(extended_records[0x71][:-2]).decode('utf-16')

        serial_number = hex(struct.unpack("<I", extended_records[0x75])[0])
        raw_modified_date = struct.unpack("<Q", extended_records[0x66])[0]/10000000
        epoch_modified_date = datetime(1601, 1, 1) + timedelta(seconds=raw_modified_date)
        modified_date = epoch_modified_date.strftime("%a %b %d %H:%M:%S %Y")

        raw_created_date = struct.unpack("<Q", extended_records[0x65])[0]/10000000
        epoch_created_date = datetime(1601, 1, 1) + timedelta(seconds=raw_created_date)
        created_date = epoch_created_date.strftime("%a %b %d %H:%M:%S %Y")

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

        return Controller(controller_name, serial_number, path, sfc_execution_control, sfc_restart_position, sfc_last_scan, created_date, modified_date, data_types, tags, programs, aois, map_devices)

@dataclass
class ProjectBuilder:
    quick_info_filename: PathLike

    def build(self) -> RSLogix5000Content:
        element = ET.parse(self.quick_info_filename)
        target_name = element.find(".").attrib["Name"]
        schema_revision = str(element.find("SchemaVersion").attrib["Major"]) + "." + str(
            element.find("SchemaVersion").attrib["Minor"])
        software_revision = str(element.find("DeviceIdentity").attrib["MajorRevision"]) + "." + str(
            element.find("DeviceIdentity").attrib["MinorRevision"])
        target_type = "Controller"
        contains_context = "false"
        now = datetime.now()
        export_date = now.strftime("%a %b %d %H:%M:%S %Y")
        export_options = "NoRawData L5KData DecoratedData ForceProtectedEncoding AllProjDocTrans"
        return RSLogix5000Content(None, schema_revision, software_revision, target_name, target_type, contains_context, export_date, export_options)


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


