import os
import shutil
import struct
from dataclasses import dataclass, field
from enum import Enum
from os import PathLike
from pathlib import Path
from sqlite3 import Cursor
from typing import List, Tuple, Dict
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

from acd.generated.comps.rx_generic import RxGeneric

from loguru import logger as log

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
                    if attribute == "tags" or attribute == "data_types" or attribute == "members" or attribute == "programs" or attribute == "routines":
                        new_child_list: List[str] = []
                        for element in attribute_value:
                            if isinstance(element, L5xElement):
                                new_child_list.append(element.to_xml())
                            else:
                                new_child_list.append(f"<{element}/>")
                        child_list.append(f'<{attribute.title().replace("_", "")}>{"".join(new_child_list)}</{attribute.title().replace("_", "")}>')

                else:
                    if attribute == "cls":
                        attribute = "class"
                    attribute_list.append(f'{attribute.title().replace("_", "")}="{attribute_value}"')

        _export_name = self.__class__.__name__.title().replace("_", "")
        return f'<{_export_name} {" ".join(attribute_list)}>{"".join(child_list)}</{_export_name}>'


@dataclass
class Member(L5xElement):
    name: str
    data_type: str
    dimension: int
    radix: str
    hidden: bool
    external_access: str


@dataclass
class DataType(L5xElement):
    name: str
    family: str
    cls: str
    members: List[Member]


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
    name: str
    type: str
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
    comm_path: str
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
    target_type: str
    contains_context: str
    export_date: str
    export_options: str

    def __post_init__(self):
        self._name = "RSLogix5000Content"


def radix_enum(i: int) -> str:
    if i == 0:
        return "NullType"
    if i == 1:
        return "General"
    if i == 2:
        return "Binary"
    if i == 3:
        return "Octal"
    if i == 4:
        return "Decimal"
    if i == 5:
        return "Hex"
    if i == 6:
        return "Exponential"
    if i == 7:
        return "Float"
    if i == 8:
        return "ASCII"
    if i == 9:
        return "Unicode"
    if i == 10:
        return "Date/Time"
    if i == 11:
        return "Date/Time (ns)"
    if i == 12:
        return "UseTypeStyle"
    return "General"


def external_access_enum(i: int) -> str:
    default = "Read/Write"
    if i == 0:
        return default
    if i == 1:
        return "Read Only"
    if i == 2:
        return "None"
    return default


@dataclass
class MemberBuilder(L5xElementBuilder):
    record: List[int] = field(default_factory=[])

    def build(self) -> Member:
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id=" + str(
                self._object_id))
        results = self._cur.fetchall()

        name = results[0][0]
        r = RxGeneric.from_bytes(results[0][3])
        try:
            r = RxGeneric.from_bytes(results[0][3])
        except Exception as e:
            return Member(name, name, "", 0, "Decimal", False, "Read/Write")

        extended_records: Dict[int, List[int]] = {}
        for extended_record in r.extended_records:
            extended_records[extended_record.attribute_id] = extended_record.value
        extended_records[r.last_extended_record.attribute_id] = r.last_extended_record.value

        cip_data_typoe = struct.unpack_from("<I", self.record, 0x78)[0]
        dimension = struct.unpack_from("<I", self.record, 0x5C)[0]
        radix = radix_enum(struct.unpack_from("<I", self.record, 0x54)[0])
        data_type_id = struct.unpack_from("<I", self.record, 0x58)[0]
        hidden = bool(struct.unpack_from("<I", self.record, 0x70)[0])
        external_access = external_access_enum(struct.unpack_from("<I", self.record, 0x74)[0])


        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id=" + str(
                data_type_id))
        data_type_results = self._cur.fetchall()
        data_type = data_type_results[0][0]


        return Member(name, name, data_type, dimension, radix, hidden, external_access)


@dataclass
class DataTypeBuilder(L5xElementBuilder):

    def build(self) -> DataType:
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id=" + str(
                self._object_id))
        results = self._cur.fetchall()

        name = results[0][0]

        try:
            r = RxGeneric.from_bytes(results[0][3])
        except Exception as e:
            return DataType(name, name, "NoFamily", "User", [])

        extended_records: Dict[int, List[int]] = {}
        for extended_record in r.extended_records:
            extended_records[extended_record.attribute_id] = extended_record.value
        extended_records[r.last_extended_record.attribute_id] = r.last_extended_record.value

        string_family_int = struct.unpack("<I", extended_records[0x6C])[0]
        string_family = "StringFamily" if string_family_int == 1 else "NoFamily"

        built_in = struct.unpack("<I", extended_records[0x67])[0]
        module_defined = struct.unpack("<I", extended_records[0x69])[0]

        class_type = "User"
        if module_defined > 0:
            class_type = "IO"
        if built_in > 0:
            class_type = "ProductDefined"
        if len(extended_records[0x64]) == 0x04:
            member_count = struct.unpack("<I", extended_records[0x64])[0]
        else:
            member_count = 0

        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE parent_id=" + str(
                self._object_id))
        member_results = self._cur.fetchall()
        children: List[Member] = []
        if len(member_results) == 1:
            member_collection_id = member_results[0][1]

            self._cur.execute(
                f"SELECT comp_name, object_id, parent_id, seq_number, record FROM comps WHERE parent_id={member_collection_id} ORDER BY seq_number")
            children_results = self._cur.fetchall()

            if member_count != len(children_results):
                raise Exception("Member and children list arent the same length")

            for idx, child in enumerate(children_results):
                children.append(MemberBuilder(self._cur, child[1], extended_records[0x6E + idx]).build())

        return DataType(name, name, string_family, class_type, children)


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

        if r.cip_type != 0x6B and r.cip_type != 0x68:
            return Tag(results[0][0], results[0][0], "Base", "", "Decimal", "None", 0, [])
        if r.main_record.data_type == 0xFFFFFFFF:
            data_type = ""
        else:
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

        radix = radix_enum(r.main_record.radix)
        external_access = external_access_enum(r.main_record.external_access)

        if r.main_record.dimension_1 != 0:
            data_type = data_type + "[" + str(r.main_record.dimension_1) + "]"
        if r.main_record.dimension_2 != 0:
            data_type = data_type + "[" + str(r.main_record.dimension_2) + "]"
        if r.main_record.dimension_3 != 0:
            data_type = data_type + "[" + str(r.main_record.dimension_3) + "]"
        return Tag(name, name, "Base",  data_type, radix, external_access, r.main_record.data_table_instance, comment_results)


def routine_type_enum(idx: int) -> str:
    if idx == 0:
        return "TypeLess"
    if idx == 1:
        return "RLL"
    if idx == 2:
        return "FBD"
    if idx == 3:
        return "SFC"
    if idx == 4:
        return "ST"
    if idx == 5:
        return "External"
    if idx == 6:
        return "Encrypted"
    return "Typeless"


@dataclass
class RoutineBuilder(L5xElementBuilder):

    def build(self) -> Routine:
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id=" + str(
                self._object_id))
        results = self._cur.fetchall()

        try:
            r = RxGeneric.from_bytes(results[0][3])
        except Exception as e:
            return Routine(results[0][0], results[0][0], "", [])

        record = results[0][3]
        name = results[0][0]
        routine_type = routine_type_enum(struct.unpack_from("<H", r.record_buffer, 0x30)[0])

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
        return Routine(name, name, routine_type, rungs)


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

        r = RxGeneric.from_bytes(results[0][3])

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

        self._cur.execute(
            "SELECT tag_reference, record_string FROM comments WHERE parent=" + str(
                (r.comment_id * 0x10000) + r.cip_type))
        comment_results = self._cur.fetchall()

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

        comm_path = bytes(extended_records[0x6a][:-2]).decode('utf-16')
        sfc_execution_control = bytes(extended_records[0x6F][:-2]).decode('utf-16')
        sfc_restart_position = bytes(extended_records[0x70][:-2]).decode('utf-16')
        sfc_last_scan = bytes(extended_records[0x71][:-2]).decode('utf-16')

        serial_number_raw = hex(struct.unpack("<I", extended_records[0x75])[0])[2:].zfill(8)
        serial_number = f"16#{serial_number_raw[:4].upper()}_{serial_number_raw[4:].upper()}"

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

        return Controller(controller_name, serial_number, comm_path, sfc_execution_control, sfc_restart_position, sfc_last_scan, created_date, modified_date, data_types, tags, programs, aois, map_devices)

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
        return RSLogix5000Content(target_name, None, schema_revision, software_revision, target_name, target_type, contains_context, export_date, export_options)


@dataclass
class DumpCompsRecords(L5xElementBuilder):
    base_directory: PathLike = Path("dump")

    def dump(self, parent_id: int = 0, log_file=None):
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
                log_file.write(
                    f"Class - {struct.unpack_from('<H', result[4], 0xA)[0]} Instance {struct.unpack_from('<H', result[4], 0xC)[0]}- {str(new_path) + '/' + name}\n")
                file.write(record)

            DumpCompsRecords(self._cur, object_id, new_path).dump(object_id, log_file)
