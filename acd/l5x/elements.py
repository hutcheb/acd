import html
import os
import re
import shutil
import struct
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from os import PathLike
from pathlib import Path
from sqlite3 import Cursor
from typing import List, Tuple, Dict, Union

from acd.l5x.catalog_numbers import CATALOG_NUMBERS, catalog_number_for_identity
from acd.l5x.port_structures import PORT_STRUCTURES
from acd.record.rx import LegacyRxGeneric, RxGeneric


# Characters that are illegal in XML 1.0: everything outside
# #x9 | #xA | #xD | #x20-#xD7FF | #xE000-#xFFFD | #x10000-#x10FFFF.
_XML_ILLEGAL_RE = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")


def _escape_xml_attr(value: object) -> str:
    """Escape a value for use inside a double-quoted XML attribute.

    Beyond ``html.escape``, this strips characters that are illegal in XML 1.0
    and encodes the legal-but-delimiting whitespace (TAB/CR/LF) as numeric
    character references. Some binary records decode to garbage when an offset
    drifts (e.g. an AOI ``Vendor`` field read with ``errors="replace"``); without
    this, those raw control characters and newlines land verbatim in an
    attribute value, producing non-well-formed L5X that breaks downstream XML
    parsers.
    """
    text = _XML_ILLEGAL_RE.sub("", str(value))
    text = html.escape(text, quote=True)
    return text.replace("\t", "&#x9;").replace("\r", "&#xD;").replace("\n", "&#xA;")


# Characters that are illegal in Windows (and some other) filesystem names.
# comp_name values are Logix tag/channel names and can legally contain
# ":" (e.g. "CHANNEL_DI_TIMESTAMP:O:0"), "/" and "\" (member access), and
# other characters that Windows refuses in a filename or directory name.
_PATH_ILLEGAL_RE = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def _sanitize_path_component(name: str) -> str:
    """Make a Logix comp_name safe to use as a single path component.

    ``DumpCompsRecords`` writes one file (and one sub-directory) per record,
    naming them after ``comp_name``. Those names come straight from the ACD
    binary and may contain characters that are illegal in filesystem paths on
    some platforms -- most commonly ``:`` on Windows (a channel name such as
    ``CHANNEL_DI_TIMESTAMP:O:0``). Without this, ``os.makedirs``/``open`` raise
    OSError [WinError 123] on Windows.

    Illegal characters are replaced with ``_`` (deterministic and lossless for
    round-tripping to the directory layout, since the original name is still
    recorded in output.log). Names that need no change pass through untouched,
    so existing dumps on Linux/macOS are unaffected.
    """
    cleaned = _PATH_ILLEGAL_RE.sub("_", name)
    # Windows also reserves device names (CON, PRN, AUX, NUL, COM1-9, LPT1-9);
    # a trailing space/dot can break open() there. Prefix such names defensively.
    stem = cleaned.strip().split(".")[0].upper()
    if stem in {"CON", "PRN", "AUX", "NUL"} or re.fullmatch(r"(COM|LPT)[1-9]", stem):
        cleaned = "_" + cleaned
    cleaned = cleaned.rstrip(" .")
    return cleaned or "_"


@dataclass
class L5xElementBuilder:
    _cur: Cursor
    _object_id: int = -1


def _get_program_records(cur: Cursor, collection_id: int) -> List[Tuple[str, int, int, bytes]]:
    cur.execute(
        "SELECT comp_name, object_id, record_type, record FROM comps "
        "WHERE parent_id=? AND record_type=256",
        (collection_id,),
    )
    return cur.fetchall()


def _required_program_collection(
    cur: Cursor,
    program_name: str,
    program_id: int,
    record_type: int,
    collection_name: str,
) -> int:
    cur.execute(
        "SELECT object_id FROM comps WHERE parent_id=? AND comp_name=?",
        (program_id, collection_name),
    )
    rows = cur.fetchall()
    context = (
        f"program {program_name!r} (object_id={program_id}, record_type={record_type})"
    )
    if not rows:
        raise ValueError(f"{context} is missing required {collection_name}")
    if len(rows) > 1:
        raise ValueError(f"{context} has multiple {collection_name} children")
    return rows[0][0]


# Maps Python attribute names to L5X XML section wrapper tag names.
# Entries here also control which list attributes are serialized as child sections.
_LIST_SECTION_NAMES = {
    "tags": "Tags",
    "local_tags": "LocalTags",
    "parameters": "Parameters",
    "data_types": "DataTypes",
    "members": "Members",
    "modules": "Modules",
    "programs": "Programs",
    "routines": "Routines",
    "aois": "AddOnInstructionDefinitions",
    "tasks": "Tasks",
    "scheduled_programs": "ScheduledPrograms",
}


@dataclass
class L5xElement:
    _name: str

    def __post_init__(self):
        self._export_name = ""

    def to_xml(self) -> str:
        attribute_list: List[str] = []
        child_list: List[str] = []
        for attribute in self.__dict__:
            if attribute[0] != "_":
                attribute_value = self.__getattribute__(attribute)
                if attribute_value is None:
                    continue
                if isinstance(attribute_value, L5xElement):
                    child_list.append(attribute_value.to_xml())
                elif isinstance(attribute_value, list):
                    if attribute in _LIST_SECTION_NAMES:
                        section_name = _LIST_SECTION_NAMES[attribute]
                        new_child_list: List[str] = []
                        for element in attribute_value:
                            if isinstance(element, L5xElement):
                                if getattr(element, "_l5x_exclude", False):
                                    continue
                                new_child_list.append(element.to_xml())
                            else:
                                new_child_list.append(f"<{element}/>")
                        child_list.append(
                            f'<{section_name}>{"".join(new_child_list)}</{section_name}>'
                        )
                else:
                    if attribute == "cls":
                        attribute = "class"
                    if isinstance(attribute_value, bool):
                        attribute_value = str(attribute_value).lower()
                    _overrides = getattr(self, "_xml_attr_overrides", {})
                    xml_attr_name = _overrides.get(attribute, attribute.title().replace("_", ""))
                    attribute_list.append(
                        f'{xml_attr_name}="{_escape_xml_attr(attribute_value)}"'
                    )

        _export_name = (
            getattr(self, "_export_name", "") or self.__class__.__name__.title().replace("_", "")
        )
        return f'<{_export_name} {" ".join(attribute_list)}>{"".join(child_list)}</{_export_name}>'


@dataclass
class Member(L5xElement):
    name: str
    data_type: str
    dimension: int
    radix: str
    hidden: bool
    target: Union[str, None]      # BIT members only; None omits the attribute
    bit_number: Union[int, None]  # BIT members only; None omits the attribute
    external_access: str
    _description: Union[str, None] = field(default=None)

    def to_xml(self) -> str:
        base = super().to_xml()
        if not self._description:
            return base
        desc_xml = f'<Description>\n<![CDATA[{self._description}]]>\n</Description>'
        idx = base.index(">")
        return base[:idx + 1] + desc_xml + base[idx + 1:]


@dataclass
class DataType(L5xElement):
    name: str
    family: str
    cls: str
    members: List[Member]
    _description: Union[str, None] = field(default=None)

    def __post_init__(self):
        super().__post_init__()
        self._export_name = "DataType"

    @property
    def _l5x_exclude(self) -> bool:
        return self.cls == "ProductDefined" or ":" in self.name

    def to_xml(self) -> str:
        base = super().to_xml()
        if not self._description:
            return base
        desc_xml = f'<Description>\n<![CDATA[{self._description}]]>\n</Description>'
        idx = base.index(">")
        return base[:idx + 1] + desc_xml + base[idx + 1:]


# Maps primitive DataType names to their L5K zero-default value string.
# UDT, STRING, ALARM_DIGITAL, MESSAGE, and array types are intentionally omitted —
# they require complex structured L5K encoding that is not yet implemented.
_PRIMITIVE_L5K_ZERO: Dict[str, str] = {
    "BOOL":  "0",
    "SINT":  "0",
    "INT":   "0",
    "DINT":  "0",
    "LINT":  "0",
    "USINT": "0",
    "UINT":  "0",
    "UDINT": "0",
    "ULINT": "0",
    "REAL":  "0.00000000e+000",
    "LREAL": "0.00000000e+000",
}

# Radix string used in Decorated DataValueMember for each numeric primitive.
# BOOL and BIT use no Radix attribute; REAL/LREAL use "Float"; all integers use "Decimal".
_PRIMITIVE_RADIX: Dict[str, str] = {
    "SINT":  "Decimal",
    "INT":   "Decimal",
    "DINT":  "Decimal",
    "LINT":  "Decimal",
    "USINT": "Decimal",
    "UINT":  "Decimal",
    "UDINT": "Decimal",
    "ULINT": "Decimal",
    "REAL":  "Float",
    "LREAL": "Float",
}

# Default zero value string for each primitive in Decorated output.
_PRIMITIVE_DECORATED_ZERO: Dict[str, str] = {
    "BOOL":  "0",
    "BIT":   "0",
    "SINT":  "0",
    "INT":   "0",
    "DINT":  "0",
    "LINT":  "0",
    "USINT": "0",
    "UINT":  "0",
    "UDINT": "0",
    "ULINT": "0",
    "REAL":  "0.0",
    "LREAL": "0.0",
}

# Built-in Logix struct types that are not in the user DataType list.
# Each entry is a list of (member_name, member_data_type) tuples.
# Only non-hidden, visible members are listed (as they appear in Decorated output).
_BUILTIN_STRUCT_MEMBERS: Dict[str, List[Tuple[str, str]]] = {
    "TIMER": [
        ("PRE", "DINT"), ("ACC", "DINT"),
        ("EN", "BOOL"), ("TT", "BOOL"), ("DN", "BOOL"),
    ],
    "COUNTER": [
        ("PRE", "DINT"), ("ACC", "DINT"),
        ("CU", "BOOL"), ("CD", "BOOL"), ("DN", "BOOL"), ("OV", "BOOL"), ("UN", "BOOL"),
    ],
    "CONTROL": [
        ("LEN", "DINT"), ("POS", "DINT"),
        ("EN", "BOOL"), ("EU", "BOOL"), ("DN", "BOOL"), ("EM", "BOOL"),
        ("ER", "BOOL"), ("UL", "BOOL"), ("IN", "BOOL"), ("FD", "BOOL"),
    ],
}

# Types for which we emit no Decorated element at all (they use other formats).
_SKIP_DECORATED: set = {"ALARM_DIGITAL", "MESSAGE", "AXIS_SERVO", "PID_ENHANCED"}


def _member_decorated_xml(member_name: str, member_dt: str, member_dim: int,
                           data_types_map: Dict[str, "DataType"]) -> str:
    """Return the Decorated XML fragment for a single UDT member.

    member_dt:  the DataType name of the member (already upper-cased by caller)
    member_dim: array dimension (0 = scalar)
    """
    if member_dim > 0:
        # Array member
        return _array_member_xml(member_name, member_dt, member_dim, data_types_map)

    if member_dt in ("BOOL", "BIT"):
        return f'<DataValueMember Name="{member_name}" DataType="BOOL" Value="0"/>'

    radix = _PRIMITIVE_RADIX.get(member_dt)
    zero = _PRIMITIVE_DECORATED_ZERO.get(member_dt)
    if radix is not None and zero is not None:
        return f'<DataValueMember Name="{member_name}" DataType="{member_dt}" Radix="{radix}" Value="{zero}"/>'

    # Struct member (nested UDT, TIMER, COUNTER, etc.)
    inner = _struct_members_xml(member_dt, data_types_map)
    if inner is None:
        return ""  # unknown / skip
    return f'<StructureMember Name="{member_name}" DataType="{member_dt}">{inner}</StructureMember>'


def _array_member_xml(member_name: str, member_dt: str, dim: int,
                      data_types_map: Dict[str, "DataType"]) -> str:
    """Generate an <ArrayMember> element for a member that is an array."""
    radix = _PRIMITIVE_RADIX.get(member_dt)
    zero = _PRIMITIVE_DECORATED_ZERO.get(member_dt)
    is_bool = member_dt in ("BOOL", "BIT")

    if is_bool:
        elems = "".join(
            f'<Element Index="[{i}]" Value="0"/>' for i in range(dim)
        )
        return (
            f'<ArrayMember Name="{member_name}" DataType="BOOL" Dimensions="{dim}" Radix="Decimal">'
            f'{elems}'
            f'</ArrayMember>'
        )

    if radix is not None and zero is not None:
        elems = "".join(
            f'<Element Index="[{i}]" Value="{zero}"/>' for i in range(dim)
        )
        return (
            f'<ArrayMember Name="{member_name}" DataType="{member_dt}" Dimensions="{dim}" Radix="{radix}">'
            f'{elems}'
            f'</ArrayMember>'
        )

    # Array of structs
    inner = _struct_members_xml(member_dt, data_types_map)
    if inner is None:
        return ""
    struct_xml = f'<Structure DataType="{member_dt}">{inner}</Structure>'
    elems = "".join(
        f'<Element Index="[{i}]">{struct_xml}</Element>' for i in range(dim)
    )
    return (
        f'<ArrayMember Name="{member_name}" DataType="{member_dt}" Dimensions="{dim}">'
        f'{elems}'
        f'</ArrayMember>'
    )


def _struct_members_xml(dt_name: str, data_types_map: Dict[str, "DataType"]) -> Union[str, None]:
    """Return the inner XML for a Structure/StructureMember of the given DataType.

    Returns None if the type is unknown or should be skipped.
    The returned string does NOT include the outer <Structure> wrapper.
    """
    if dt_name in _SKIP_DECORATED:
        return None

    # Handle STRING as a special built-in: LEN (DINT) + DATA (STRING/ASCII)
    if dt_name == "STRING":
        return (
            '<DataValueMember Name="LEN" DataType="DINT" Radix="Decimal" Value="0"/>'
            '<DataValueMember Name="DATA" DataType="STRING" Radix="ASCII">\n\n</DataValueMember>'
        )

    # Built-in struct types (TIMER, COUNTER, CONTROL)
    builtin_members = _BUILTIN_STRUCT_MEMBERS.get(dt_name)
    if builtin_members is not None:
        parts: List[str] = []
        for mname, mdt in builtin_members:
            radix = _PRIMITIVE_RADIX.get(mdt)
            zero = _PRIMITIVE_DECORATED_ZERO.get(mdt)
            if radix is not None and zero is not None:
                parts.append(
                    f'<DataValueMember Name="{mname}" DataType="{mdt}" Radix="{radix}" Value="{zero}"/>'
                )
            else:
                # BOOL member
                parts.append(f'<DataValueMember Name="{mname}" DataType="{mdt}" Value="0"/>')
        return "".join(parts)

    # User-defined type: look up in data_types_map
    dt_obj = data_types_map.get(dt_name)
    if dt_obj is None:
        return None

    parts = []
    for member in dt_obj.members:
        if member.hidden:
            continue
        mdt = member.data_type.upper()
        mname = member.name
        mdim = member.dimension

        fragment = _member_decorated_xml(mname, mdt, mdim, data_types_map)
        if fragment:
            parts.append(fragment)
    return "".join(parts)


def _generate_decorated(dt_base: str, dimensions: Union[str, None],
                        data_types_map: Dict[str, "DataType"]) -> str:
    """Generate a complete <Data Format="Decorated"> XML string for a tag.

    dt_base:    the base DataType name (uppercase, array brackets already stripped)
    dimensions: comma-separated dimension string (e.g. "100" or "4,8") or None for scalar
    Returns "" if this type should not have a Decorated element.
    """
    if dt_base in _SKIP_DECORATED:
        return ""

    if dimensions is None:
        # Scalar struct
        inner = _struct_members_xml(dt_base, data_types_map)
        if inner is None:
            return ""
        body = f'<Structure DataType="{dt_base}">{inner}</Structure>'
    else:
        # Array tag: parse dimensions (up to 3D, comma-separated)
        dim_parts = [int(d) for d in dimensions.split(",") if d.strip().isdigit()]
        if not dim_parts:
            return ""

        # For multi-dimensional arrays the total element count is the product.
        # We generate flat [0]..[N-1] indices for 1D, and nested for multi-D.
        # Logix displays multi-dim as [i][j] etc.
        total = 1
        for d in dim_parts:
            total *= d

        dim_str = ",".join(str(d) for d in dim_parts)

        radix = _PRIMITIVE_RADIX.get(dt_base)
        zero = _PRIMITIVE_DECORATED_ZERO.get(dt_base)
        is_bool = dt_base in ("BOOL", "BIT")

        if is_bool:
            # BOOL array: flat indexed elements with Radix="Decimal"
            def _bool_elems(parts: List[int], remaining: List[int]) -> str:
                if not remaining:
                    idx = "[" + "][".join(str(p) for p in parts) + "]"
                    return f'<Element Index="{idx}" Value="0"/>'
                return "".join(
                    _bool_elems(parts + [i], remaining[1:]) for i in range(remaining[0])
                )
            elems = _bool_elems([], dim_parts)
            body = f'<Array DataType="BOOL" Dimensions="{dim_str}" Radix="Decimal">{elems}</Array>'

        elif radix is not None and zero is not None:
            # Primitive array (DINT, REAL, etc.)
            def _prim_elems(parts: List[int], remaining: List[int]) -> str:
                if not remaining:
                    idx = "[" + "][".join(str(p) for p in parts) + "]"
                    return f'<Element Index="{idx}" Value="{zero}"/>'
                return "".join(
                    _prim_elems(parts + [i], remaining[1:]) for i in range(remaining[0])
                )
            elems = _prim_elems([], dim_parts)
            body = f'<Array DataType="{dt_base}" Dimensions="{dim_str}" Radix="{radix}">{elems}</Array>'

        else:
            # Struct array (UDT, TIMER, COUNTER, STRING, ...)
            inner = _struct_members_xml(dt_base, data_types_map)
            if inner is None:
                return ""
            struct_xml = f'<Structure DataType="{dt_base}">{inner}</Structure>'

            def _struct_elems(parts: List[int], remaining: List[int]) -> str:
                if not remaining:
                    idx = "[" + "][".join(str(p) for p in parts) + "]"
                    return f'<Element Index="{idx}">{struct_xml}</Element>'
                return "".join(
                    _struct_elems(parts + [i], remaining[1:]) for i in range(remaining[0])
                )
            elems = _struct_elems([], dim_parts)
            body = f'<Array DataType="{dt_base}" Dimensions="{dim_str}">{elems}</Array>'

    return f'<Data Format="Decorated">\n{body}\n</Data>'


@dataclass
class ProduceInfo(L5xElement):
    produce_count: str
    programmatically_send_event_trigger: str
    unicast_permitted: str
    minimum_rpi: str
    maximum_rpi: str
    default_rpi: str

    def __post_init__(self):
        super().__post_init__()
        self._export_name = "ProduceInfo"
        self._xml_attr_overrides = {
            "minimum_rpi": "MinimumRPI",
            "maximum_rpi": "MaximumRPI",
            "default_rpi": "DefaultRPI",
        }


@dataclass
class ConsumeInfo(L5xElement):
    producer: str
    remote_tag: str
    remote_instance: str
    rpi: str
    unicast: str

    def __post_init__(self):
        super().__post_init__()
        self._export_name = "ConsumeInfo"
        self._xml_attr_overrides = {"rpi": "RPI"}


@dataclass
class Tag(L5xElement):
    name: str
    tag_type: str
    data_type: Union[str, None]
    radix: Union[str, None]
    external_access: str
    constant: Union[str, None]  # "true" for constants; None omits the attribute
    dimensions: Union[str, None]
    _data_table_instance: int
    _comments: List[Tuple[str, str]]
    _data_types_map: Dict[str, "DataType"] = field(default_factory=dict)
    alias_for: Union[str, None] = None
    produce_info: Union[ProduceInfo, None] = None
    consume_info: Union[ConsumeInfo, None] = None

    @property
    def _l5x_exclude(self) -> bool:
        """Exclude tags with empty or non-identifier names (hex-address placeholders, etc.)."""
        return (
            not self.name
            or not (self.name[0].isalpha() or self.name[0] == "_")
            or ":" in self.name
            or self.name.startswith("__l0")
            or self.name.startswith("__CLONE")
            or self.name.startswith("__SL")
        )

    @staticmethod
    def _sanitize_xml_text(text: str) -> str:
        """Encode characters illegal in XML 1.0 as XML character references (&#xNN;).

        XML 1.0 allows only #x9, #xA, #xD, and #x20–#xD7FF, #xE000–#xFFFD.
        Control characters outside that range (e.g. #x02 STX) are emitted as
        character references rather than stripped, matching Logix Designer output.
        """
        parts = []
        for ch in text:
            cp = ord(ch)
            if ch in ("\t", "\n", "\r") or (0x20 <= cp <= 0xD7FF) or (0xE000 <= cp <= 0xFFFD):
                parts.append(ch)
            else:
                parts.append(f"&#x{cp:04X};")
        return "".join(parts)

    def to_xml(self) -> str:
        base = super().to_xml()

        # --- Description child element ---
        # Find tag-level description: empty tag_reference means the tag itself.
        # Tags with multiple empty-ref entries (e.g. array-element bit descriptions
        # alongside the tag description) store the real tag description as the
        # longest entry — short entries like "Spare" or "End CIP" are element labels.
        candidates = [text for ref, text in self._comments if ref in ("", ".") and text]
        desc_raw = max(candidates, key=len) if candidates else None
        desc = self._sanitize_xml_text(desc_raw) if desc_raw else None
        desc_xml = f'<Description>\n<![CDATA[{desc}]]>\n</Description>' if desc else ""

        # --- Data child element(s) ---
        # Scalar primitives get Format="L5K" only.
        # Scalar STRING gets Format="L5K" (the L5K encoder handles it separately; we emit
        # nothing here — Decorated is not used for scalar STRING tags).
        # Everything else (UDTs, arrays, TIMER, COUNTER, etc.) gets Format="Decorated".
        dt_base = self.data_type.split("[")[0].upper() if self.data_type else ""
        l5k_zero = _PRIMITIVE_L5K_ZERO.get(dt_base) if not self.dimensions else None
        data_xml = f'<Data Format="L5K">\n{l5k_zero}\n</Data>' if l5k_zero is not None else ""

        if not data_xml and dt_base not in _SKIP_DECORATED and dt_base != "STRING":
            # Generate Decorated data for non-primitive / array types
            decorated = _generate_decorated(dt_base, self.dimensions, self._data_types_map)
            if decorated:
                data_xml = decorated

        if not desc_xml and not data_xml:
            return base

        # Insert Description (if any) then Data (if any) immediately after the opening tag.
        opening_end = base.index(">") + 1
        if desc_xml:
            base = base[:opening_end] + desc_xml + base[opening_end:]

        insert_at = opening_end + len(desc_xml)
        for child_name in ("ProduceInfo", "ConsumeInfo"):
            child_end = base.find(f"</{child_name}>", insert_at)
            if child_end >= 0:
                insert_at = child_end + len(child_name) + 3
        return base[:insert_at] + data_xml + base[insert_at:]


@dataclass
class LocalTag(L5xElement):
    """Represents a local (non-public) tag inside an AOI (<LocalTag> in L5X)."""
    name: str
    data_type: str
    dimensions: Union[str, None]  # array size; None for scalars (omitted from XML)
    radix: Union[str, None]   # None for complex/UDT types (omitted from XML)
    external_access: str
    _description: Union[str, None] = field(default=None)

    def __post_init__(self):
        super().__post_init__()
        self._export_name = "LocalTag"

    @property
    def _l5x_exclude(self) -> bool:
        """Exclude hex-address placeholders, empty names, and ACD-internal runtime tags."""
        return (
            not self.name
            or not (self.name[0].isalpha() or self.name[0] == "_")
            or ":" in self.name
            or self.name.startswith("__l0")
            or self.name.startswith("__CLONE")
        )

    def to_xml(self) -> str:
        base = super().to_xml()
        if not self._description:
            return base
        desc_xml = f'<Description>\n<![CDATA[{self._description}]]>\n</Description>'
        idx = base.index(">")
        return base[:idx + 1] + desc_xml + base[idx + 1:]


@dataclass
class Parameter(L5xElement):
    """Represents a public parameter of an AOI (<Parameter> in L5X)."""
    name: str
    tag_type: str       # always "Base"
    data_type: str
    usage: str          # "Input", "Output", or "InOut"
    radix: Union[str, None]   # None for complex types (omitted from XML)
    required: str       # "true" or "false"
    visible: str        # "true" or "false"
    external_access: Union[str, None]  # None for InOut (omitted, replaced by Constant)
    constant: Union[str, None]  # "false" for non-MESSAGE InOut, None otherwise (omitted)
    dimensions: Union[str, None]  # array size; None for scalars (omitted from XML)
    _description: Union[str, None] = field(default=None)

    def __post_init__(self):
        super().__post_init__()
        self._export_name = "Parameter"

    @property
    def _l5x_exclude(self) -> bool:
        return (
            not self.name
            or not (self.name[0].isalpha() or self.name[0] == "_")
        )

    def to_xml(self) -> str:
        base = super().to_xml()
        if not self._description:
            return base
        desc_xml = f'<Description>\n<![CDATA[{self._description}]]>\n</Description>'
        idx = base.index(">")
        return base[:idx + 1] + desc_xml + base[idx + 1:]


@dataclass
class Module(L5xElement):
    """Represents a Logix hardware module (<Module> in L5X)."""
    name: str
    catalog_number: str
    vendor: int
    product_type: int
    product_code: int
    major: int
    minor: int
    parent_module: str
    parent_mod_port_id: int
    inhibited: str
    major_fault: str
    # Private fields (not serialised as XML attributes)
    _ekey_state: str = field(default="CompatibleModule")
    _slot: int = field(default=0)
    _ip_address: str = field(default="")
    _backplane_slot: Union[int, None] = field(default=None)
    _chassis_size: Union[int, None] = field(default=None)
    _port_child_counts: Dict[int, int] = field(default_factory=dict)
    # Communications / ExtendedProperties / Description (optional)
    _description: str = field(default="")
    _comm_method: Union[str, None] = field(default=None)
    # Each entry: (name, rpi_str, conn_type_str)
    _connections: List[Tuple[str, str, str]] = field(default_factory=list)
    _extended_properties: str = field(default="")

    def __post_init__(self):
        super().__post_init__()
        self._export_name = "Module"

    def to_xml(self) -> str:
        # Hash-named drive peripherals have no Name attribute in Logix-exported L5X.
        name_attr = "" if self.name == "?" else f'Name="{self.name}" '
        attrs = (
            f'{name_attr}'
            f'CatalogNumber="{self.catalog_number}" '
            f'Vendor="{self.vendor}" '
            f'ProductType="{self.product_type}" '
            f'ProductCode="{self.product_code}" '
            f'Major="{self.major}" '
            f'Minor="{self.minor}" '
            f'ParentModule="{self.parent_module}" '
            f'ParentModPortId="{self.parent_mod_port_id}" '
            f'Inhibited="{self.inhibited}" '
            f'MajorFault="{self.major_fault}"'
        )

        # Optional <Description>
        desc_xml = ""
        if self._description:
            desc_xml = f'<Description>\n<![CDATA[{self._description}]]>\n</Description>'

        ekey = f'<EKey State="{self._ekey_state}"/>'
        ports = self._build_ports_xml()

        # <Communications> section — only emitted when a CommMethod is known.
        comm_xml = ""
        if self._comm_method is not None:
            conn_parts: List[str] = []
            for (conn_name, rpi_str, conn_type) in self._connections:
                safe_name = _escape_xml_attr(conn_name)
                # Derive InputTag / OutputTag stubs based on connection type.
                if conn_type == "Output":
                    tag_stubs = (
                        '<OutputTag ExternalAccess="Read/Write">'
                        '<Comments/>'
                        '</OutputTag>'
                    )
                else:
                    # Input or InputOutput: include both stubs.
                    tag_stubs = (
                        '<InputTag ExternalAccess="Read Only">'
                        '<Comments/>'
                        '</InputTag>'
                        '<OutputTag ExternalAccess="Read/Write">'
                        '<Comments/>'
                        '</OutputTag>'
                    )
                conn_parts.append(
                    f'<Connection Name="{safe_name}" RPI="{rpi_str}" Type="{conn_type}"'
                    f' EventID="0" ProgrammaticallySendEventTrigger="false" Unicast="false">'
                    f'{tag_stubs}'
                    f'</Connection>'
                )
            joined = "".join(conn_parts)
            connections_xml = f'<Connections>{joined}</Connections>' if joined else '<Connections/>'
            comm_xml = (
                f'<Communications CommMethod="{self._comm_method}">'
                f'{connections_xml}'
                f'</Communications>'
            )

        # <ExtendedProperties> section — only emitted when public data is known.
        ext_xml = ""
        if self._extended_properties:
            ext_xml = f'<ExtendedProperties><public>{self._extended_properties}</public></ExtendedProperties>'

        return f'<Module {attrs}>{desc_xml}{ekey}{ports}{comm_xml}{ext_xml}</Module>'

    def _build_ports_xml(self) -> str:
        """Build the <Ports>...</Ports> XML section for this module.

        Looks up the port structure from PORT_STRUCTURES by (vendor, product_type,
        product_code). Falls back to <Ports/> if the catalog number is not in the table.
        """
        key = (self.vendor, self.product_type, self.product_code)
        port_defs = PORT_STRUCTURES.get(key)
        if port_defs is None:
            return '<Ports/>'

        is_root = (self.major_fault == "true")
        port_parts: List[str] = []

        for pd in port_defs:
            # --- Upstream direction ---
            # Root modules (self-parenting CPU) have all ports downstream.
            # For other modules: if upstream_fixed=True, use the static upstream_port value.
            # If upstream_fixed=False, determine from parent_mod_port_id (the port on the
            # parent module that this module connects through — when that matches port_id,
            # this port faces upstream).
            if is_root:
                upstream_str = "false"
            elif pd.upstream_fixed:
                upstream_str = "true" if pd.upstream_port else "false"
            else:
                upstream_str = "true" if pd.port_id == self.parent_mod_port_id else "false"

            # --- Address attribute ---
            if pd.address_mode == "omit":
                addr_attr = ""
            elif pd.address_mode == "slot":
                # Non-upstream ICP ports (remote chassis owner): use _backplane_slot if known.
                if upstream_str == "false" and self._backplane_slot is not None:
                    addr_attr = f' Address="{self._backplane_slot}"'
                else:
                    addr_attr = f' Address="{self._slot if self._slot != 0xFFFFFFFF else 0}"'
            elif pd.address_mode == "zero":
                addr_attr = ' Address="0"'
            else:  # "empty" — use IP from binary if present, else omit value
                addr_attr = f' Address="{self._ip_address}"'

            # --- Bus element ---
            # Bus is only emitted on downstream (Upstream="false") ports.
            # upstream ports never carry a Bus element.
            is_upstream = (upstream_str == "true")
            bus_xml = self._bus_xml(pd, is_upstream)

            if bus_xml:
                port_parts.append(
                    f'<Port Id="{pd.port_id}"{addr_attr} Type="{pd.port_type}" Upstream="{upstream_str}">\n'
                    f'{bus_xml}\n'
                    f'</Port>\n'
                )
            else:
                port_parts.append(
                    f'<Port Id="{pd.port_id}"{addr_attr} Type="{pd.port_type}" Upstream="{upstream_str}"/>\n'
                )

        return f'<Ports>\n{"".join(port_parts)}</Ports>\n'

    def _bus_xml(self, pd, is_upstream: bool) -> str:
        """Return the Bus XML string for a port, or '' if no Bus element should be emitted.

        Bus elements are only present on downstream (Upstream=false) ports.
        """
        if is_upstream:
            return ""
        mode = pd.bus_mode
        if mode == "none":
            return ""
        if mode == "always":
            return "<Bus/>"
        if mode.startswith("fixed:"):
            # Use binary chassis size when available (read from RxDataCollection);
            # fall back to the hardcoded port_structures value.
            if self._chassis_size is not None:
                return f'<Bus Size="{self._chassis_size}"/>'
            size = mode.split(":")[1]
            return f'<Bus Size="{size}"/>'
        if mode == "children_or_none":
            child_count = self._port_child_counts.get(pd.port_id, 0)
            if self._chassis_size is not None:
                child_count = max(child_count, self._chassis_size)
            if child_count == 0:
                return ""
            return f'<Bus Size="{child_count}"/>'
        # "children" mode: child count, but never less than _chassis_size when known
        # (handles remote chassis with empty slots not represented as child modules).
        child_count = self._port_child_counts.get(pd.port_id, 0)
        if self._chassis_size is not None:
            child_count = max(child_count, self._chassis_size)
        return f'<Bus Size="{child_count}"/>'


@dataclass
class Routine(L5xElement):
    name: str
    type: str
    rungs: List[str]
    _rung_ids: List[int] = field(default_factory=list)
    _rung_comments: Dict[int, str] = field(default_factory=dict)

    def to_xml(self) -> str:
        rll_content = ""
        if self.type == "RLL" and self.rungs:
            rung_xmls = []
            for i, rung_text in enumerate(self.rungs):
                text = (rung_text or "").strip()
                if not text:
                    continue
                comment_xml = ""
                if i in self._rung_comments:
                    comment_text = self._rung_comments[i]
                    comment_xml = f'<Comment><![CDATA[{comment_text}]]></Comment>'
                rung_xmls.append(
                    f'<Rung Number="{i}" Type="N">'
                    f'{comment_xml}'
                    f'<Text><![CDATA[{text}]]></Text>'
                    f'</Rung>'
                )
            if rung_xmls:
                rll_content = f'<RLLContent>{"".join(rung_xmls)}</RLLContent>'
        return f'<Routine Name="{_escape_xml_attr(self.name)}" Type="{self.type}">{rll_content}</Routine>'


@dataclass
class AOI(L5xElement):
    name: str
    revision: str
    revision_extension: Union[str, None]  # None if absent (omitted from XML)
    vendor: Union[str, None]  # None if absent (omitted from XML)
    execute_prescan: str
    execute_postscan: str
    execute_enable_in_false: str
    created_date: str
    created_by: str
    edited_date: str
    edited_by: str
    software_revision: str
    parameters: List[Parameter]
    local_tags: List[LocalTag]
    routines: List[Routine]
    _description: Union[str, None] = field(default=None)
    _revision_note: str = field(default="")

    def __post_init__(self):
        super().__post_init__()
        self._export_name = "AddOnInstructionDefinition"

    def to_xml(self) -> str:
        base = super().to_xml()
        idx = base.index(">")
        inject = ""
        if self._description:
            inject += f'<Description>\n<![CDATA[{self._description}]]>\n</Description>'
        if self._revision_note:
            inject += f'<RevisionNote>\n<![CDATA[{self._revision_note}]]>\n</RevisionNote>'
        return base[:idx + 1] + inject + base[idx + 1:]


@dataclass
class Program(L5xElement):
    name: str
    test_edits: str
    main_routine_name: Union[str, None]  # None if absent (omitted from XML)
    fault_routine_name: Union[str, None]  # None if absent (omitted from XML)
    disabled: str
    synchronize_redundancy_data_after_execution: Union[str, None]  # None → omit attr
    use_as_folder: str
    tags: List[Tag]        # Tags section before Routines (matches L5X export order)
    routines: List[Routine]


@dataclass
class ScheduledProgram(L5xElement):
    name: str

    def __post_init__(self):
        super().__post_init__()
        self._export_name = "ScheduledProgram"


@dataclass
class EventInfo(L5xElement):
    event_trigger: str
    enable_timeout: str

    def __post_init__(self):
        super().__post_init__()
        self._export_name = "EventInfo"


@dataclass
class Task(L5xElement):
    name: str
    type: str
    rate: Union[str, None]  # None for CONTINUOUS tasks (omitted from XML)
    priority: str
    watchdog: str
    disable_update_outputs: str
    inhibit_task: str
    event_info: Union[EventInfo, None]  # None for non-EVENT tasks
    scheduled_programs: List[ScheduledProgram]


@dataclass
class Controller(L5xElement):
    use: str
    name: str
    processor_type: Union[str, None]  # None if unknown (omitted from XML)
    major_rev: str
    minor_rev: str
    major_fault_program: Union[str, None]  # None if not set (omitted from XML)
    project_creation_date: str
    last_modified_date: str
    sfc_execution_control: str
    sfc_restart_position: str
    sfc_last_scan: str
    comm_path: Union[str, None]  # None if not set (omitted from XML)
    project_sn: str
    match_project_to_controller: str
    can_use_rpi_from_producer: str
    inhibit_automatic_firmware_update: str
    pass_through_configuration: str
    download_project_documentation_and_extended_properties: str
    download_project_custom_properties: str
    report_minor_overflow: str
    auto_diags_enabled: str
    web_server_enabled: str
    data_types: List[DataType]
    modules: List[Module]
    tags: List[Tag]
    programs: List[Program]
    tasks: List[Task]
    aois: List[AOI]
    # _redundancy_enabled is NOT serialised as a regular XML attribute (underscore prefix
    # skips it in the base to_xml()); it is used only to build the <RedundancyInfo> element.
    _redundancy_enabled: bool = field(default=False)

    def __post_init__(self):
        super().__post_init__()
        self._xml_attr_overrides = {
            "sfc_execution_control": "SFCExecutionControl",
            "sfc_restart_position": "SFCRestartPosition",
            "sfc_last_scan": "SFCLastScan",
            "project_sn": "ProjectSN",
            "can_use_rpi_from_producer": "CanUseRPIFromProducer",
        }

    def to_xml(self) -> str:
        # The <Controller> child element ORDER is fixed by the Studio 5000 schema
        # (validated against the known-good reference files in resources/, e.g.
        # ACDTestsWithAOI.L5X). It is:
        #   Description, RedundancyInfo, Security, SafetyInfo, DataTypes, Modules,
        #   AddOnInstructionDefinitions, Tags, Programs, Tasks, CST, WallClockTime,
        #   Trends, DataLogs, TimeSynchronize, EthernetPorts
        # NOTE: AddOnInstructionDefinitions comes right AFTER Modules (not after
        # Tasks as the field-declaration order would suggest), and the structural
        # stubs (RedundancyInfo/Security/SafetyInfo) come BEFORE the data sections.
        # The base to_xml() emits children in dataclass field order, which is the
        # WRONG order for Studio import, so we build the inner content explicitly.
        base = super().to_xml()
        idx = base.index(">")
        open_tag = base[: idx + 1]

        redundancy_enabled_str = "true" if self._redundancy_enabled else "false"
        # Reference files carry an empty <Description> stub as the first child.
        parts = [
            open_tag,
            "<Description></Description>",
            f'<RedundancyInfo Enabled="{redundancy_enabled_str}" KeepTestEditsOnSwitchOver="false"/>',
            '<Security Code="0" ChangesToDetect="16#ffff_ffff_ffff_ffff"/>',
            '<SafetyInfo/>',
            self._section_xml("data_types", "DataTypes"),
            self._section_xml("modules", "Modules"),
            self._section_xml("aois", "AddOnInstructionDefinitions"),  # AFTER Modules
            self._section_xml("tags", "Tags"),
            self._section_xml("programs", "Programs"),
            self._section_xml("tasks", "Tasks"),
            '<CST MasterID="0"/>',
            '<WallClockTime LocalTimeAdjustment="0" TimeZone="0"/>',
            '<Trends/>',
            '<DataLogs/>',
            '<TimeSynchronize Priority1="128" Priority2="128" PTPEnable="true"/>',
            self._ethernet_ports_xml(),
            '</Controller>',
        ]
        return "".join(parts)

    def _ethernet_ports_xml(self) -> str:
        """Build the <EthernetPorts> section.

        A root ControlLogix CPU with an integrated Ethernet port (L83E/L84E/L85E/
        L82E/L86E etc.) requires an <EthernetPort> descriptor. Omitting it (an empty
        <Ports/>) makes Studio 5000 rename+delete the CPU module on import ("Collision
        ... renamed to Local1 / Deleting module"). The known-good reference files
        (e.g. ACDTestsWithAOI.L5X) carry:
            <EthernetPorts><EthernetPort Port="1" Label="1" PortEnabled="true"/></EthernetPorts>
        Emit that descriptor when the root CPU has an Ethernet port; otherwise an
        empty <EthernetPorts/> (a CPU without integrated Ethernet, e.g. L74, has none).
        """
        for mod in self.modules:
            if mod.major_fault != "true":
                continue  # not the root CPU
            # The CPU's integrated Ethernet port is the one with an Ethernet port
            # definition. Detect via the port structure table.
            from acd.l5x.port_structures import PORT_STRUCTURES

            defs = PORT_STRUCTURES.get((mod.vendor, mod.product_type, mod.product_code)) or []
            eth_ports = [d for d in defs if d.port_type == "Ethernet"]
            if not eth_ports:
                return "<EthernetPorts/>"
            # One descriptor per integrated Ethernet port (these CPUs have exactly one).
            # Port="1" is the CPU's own (first) Ethernet port in the EthernetPorts
            # context; Label mirrors it; PortEnabled=true (active by default).
            inner = "".join(
                f'<EthernetPort Port="{n}" Label="{n}" PortEnabled="true"/>'
                for n in range(1, len(eth_ports) + 1)
            )
            return f"<EthernetPorts>{inner}</EthernetPorts>"
        return "<EthernetPorts/>"

    def _section_xml(self, field_name: str, tag_name: str) -> str:
        """Serialize a list-of-L5xElement field as <Tag>...</Tag> (or <Tag/>)."""
        items = getattr(self, field_name, None) or []
        if not items:
            return f"<{tag_name}/>"
        inner = "".join(item.to_xml() for item in items)
        return f"<{tag_name}>{inner}</{tag_name}>"


@dataclass
class RSLogix5000Content(L5xElement):
    """Controller Project"""

    controller: Union[Controller, None]
    schema_revision: str
    software_revision: str
    target_name: str
    target_type: str
    contains_context: str
    export_date: str
    export_options: str

    def __post_init__(self):
        super().__post_init__()
        self._export_name = "RSLogix5000Content"


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
    if i == 2:
        return "Read Only"
    if i == 3:
        return "None"
    return default


@dataclass
class MemberBuilder(L5xElementBuilder):
    record: bytes = field(default_factory=bytes)
    # Map from offset-0x60 value to backing member name, used to resolve BIT Target.
    # Built by DataTypeBuilder before iterating children and passed in here.
    _offset60_to_name: Dict[int, str] = field(default_factory=dict)
    # Fallback target name for Pattern-2 BIT members (0x68==0, 0x6c==0xFFFFFFFF).
    # Set by DataTypeBuilder to the most recent preceding hidden SINT/INT in member order.
    _fallback_target: Union[str, None] = field(default=None)

    def build(self) -> Member:
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id="
            + str(self._object_id)
        )
        results = self._cur.fetchall()

        name = results[0][0]
        r = RxGeneric.from_bytes(results[0][3])
        try:
            r = RxGeneric.from_bytes(results[0][3])
        except Exception as e:
            return Member(name, name, "", 0, "Decimal", False, None, None, "Read/Write")

        extended_records: Dict[int, List[int]] = {}
        for extended_record in r.extended_records:
            extended_records[extended_record.attribute_id] = extended_record.value

        cip_data_typoe = struct.unpack_from("<I", self.record, 0x78)[0]
        dimension = struct.unpack_from("<I", self.record, 0x5C)[0]
        radix = radix_enum(struct.unpack_from("<I", self.record, 0x54)[0])
        data_type_id = struct.unpack_from("<I", self.record, 0x58)[0]
        hidden = bool(struct.unpack_from("<I", self.record, 0x70)[0])
        external_access = external_access_enum(
            struct.unpack_from("<I", self.record, 0x74)[0]
        )

        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id="
            + str(data_type_id)
        )
        data_type_results = self._cur.fetchall()
        data_type = data_type_results[0][0]

        # BIT members: data_type resolves to BOOL but the encoding varies by sub-type.
        #
        # Pattern 1 (0x6c != 0xFFFFFFFF): 0x6c holds the 0x60 byte-offset of the backing
        #   field.  Resolve target via offset60_to_name.
        #
        # Pattern 2 (0x6c == 0xFFFFFFFF and 0x68 == 0): BIT member where the backing field
        #   pointer is absent.  Use _fallback_target (the most-recent preceding hidden SINT).
        #
        # Pattern 3 (0x6c == 0xFFFFFFFF and 0x68 == 1): BIT member where 0x60 directly
        #   matches the backing field's 0x60 value.  Resolve target via offset60_to_name
        #   using the member's own 0x60 value as the lookup key.
        #
        # Plain BOOL (0x6c == 0xFFFFFFFF and 0x68 == 0x800): not a BIT member; leave as BOOL.
        target: Union[str, None] = None
        bit_number: Union[int, None] = None
        if data_type == "BOOL":
            target_key = struct.unpack_from("<I", self.record, 0x6C)[0]
            val_68 = struct.unpack_from("<I", self.record, 0x68)[0]
            if target_key != 0xFFFFFFFF:
                # Pattern 1: direct backing-field reference via offset-60 map
                data_type = "BIT"
                # offset 0x5C holds a bit-offset into the host register, not an array
                # size — force dimension to 0 so _member_decorated_xml treats this as
                # a scalar rather than emitting thousands of <Element> entries.
                dimension = 0
                bit_number = struct.unpack_from("<I", self.record, 0x64)[0]
                target = self._offset60_to_name.get(target_key)
            elif val_68 == 0:
                # Pattern 2: BIT member without explicit backing-field pointer
                data_type = "BIT"
                dimension = 0  # same bit-offset field; not an array size
                bit_number = struct.unpack_from("<I", self.record, 0x64)[0]
                target = self._fallback_target
            elif val_68 == 1:
                # Pattern 3: BIT member — 0x60 of this member equals 0x60 of the backing
                # hidden field, allowing direct lookup in offset60_to_name.
                data_type = "BIT"
                dimension = 0
                bit_number = struct.unpack_from("<I", self.record, 0x64)[0]
                val_60 = struct.unpack_from("<I", self.record, 0x60)[0]
                target = self._offset60_to_name.get(val_60)

        # --- Description ---
        # The member's description is identified in the comments table by a
        # member_ref value extracted from bytes [14:18] of the comps record.
        # This value is non-zero for sub-elements (members) and zero for the
        # owning object's own description.
        description: Union[str, None] = None
        raw_comps = bytes(results[0][3])
        if len(raw_comps) >= 18:
            member_ref = struct.unpack_from("<I", raw_comps, 14)[0]
            if member_ref:
                self._cur.execute(
                    "SELECT record_string FROM comments WHERE parent=? AND member_ref=? LIMIT 1",
                    ((r.comment_id * 0x10000) + r.cip_type, member_ref),
                )
                desc_row = self._cur.fetchone()
                if desc_row and desc_row[0]:
                    description = desc_row[0]

        return Member(name, name, data_type, dimension, radix, hidden, target, bit_number, external_access, description)


@dataclass
class DataTypeBuilder(L5xElementBuilder):
    def build(self) -> DataType:
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id="
            + str(self._object_id)
        )
        results = self._cur.fetchall()

        name = results[0][0]

        try:
            r = RxGeneric.from_bytes(results[0][3])
        except Exception as e:
            return DataType(name, name, "NoFamily", "User", [])

        extended_records: Dict[int, bytes] = {}
        for extended_record in r.extended_records:
            extended_records[extended_record.attribute_id] = bytes(
                extended_record.value
            )

        string_family_int = struct.unpack("<I", extended_records[0x6C])[0]
        string_family = "StringFamily" if string_family_int == 1 else "NoFamily"

        built_in = struct.unpack("<I", extended_records[0x67])[0]
        module_defined = struct.unpack("<I", extended_records[0x69])[0]

        class_type = "User"
        if module_defined > 0:
            class_type = "IO"
        if built_in & 0x03:
            class_type = "ProductDefined"
        if 0x64 in extended_records and len(extended_records[0x64]) == 0x04:
            member_count = struct.unpack("<I", extended_records[0x64])[0]
        else:
            member_count = 0

        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE parent_id="
            + str(self._object_id)
        )
        member_results = self._cur.fetchall()
        children: List[Member] = []
        if len(member_results) == 1:
            member_collection_id = member_results[0][1]

            self._cur.execute(
                f"SELECT comp_name, object_id, parent_id, seq_number, record FROM comps WHERE parent_id={member_collection_id} ORDER BY seq_number"
            )
            children_results = self._cur.fetchall()

            # Build offset60→name map so BIT members can resolve their Target name.
            # Each member's extended record stores the byte offset of that member's data
            # within the UDT at [0x60]; BIT members reference their backing field's
            # offset via [0x6c].  Non-BIT members have [0x6c]=0xFFFFFFFF and 0x68=0x800.
            # Only include non-BIT members (0x68==0x800) so that BIT members sharing the
            # same 0x60 value as their backing field do not overwrite the backing entry.
            offset60_to_name: Dict[int, str] = {}
            for idx2, child2 in enumerate(children_results):
                key2 = 0x6E + idx2
                if key2 not in extended_records:
                    break
                rec2 = bytes(extended_records[key2])
                if len(rec2) >= 0x70:
                    target_key2 = struct.unpack_from("<I", rec2, 0x6C)[0]
                    val_68_2 = struct.unpack_from("<I", rec2, 0x68)[0]
                    if target_key2 == 0xFFFFFFFF and val_68_2 == 0x800:
                        val_60 = struct.unpack_from("<I", rec2, 0x60)[0]
                        offset60_to_name[val_60] = child2[0]

            # Some ACD files have mismatched member_count vs children list — iterate what we have.
            # Track the most recent preceding hidden SINT (fallback target for Pattern-2 BIT members).
            last_hidden_backing: Union[str, None] = None
            for idx, child in enumerate(children_results):
                key = 0x6E + idx
                if key not in extended_records:
                    break
                rec = bytes(extended_records[key])
                # Update last_hidden_backing when we see a hidden member
                if len(rec) >= 0x74:
                    is_hidden = bool(struct.unpack_from("<I", rec, 0x70)[0])
                    if is_hidden:
                        last_hidden_backing = child[0]
                try:
                    children.append(
                        MemberBuilder(
                            self._cur, child[1], bytes(extended_records[key]),
                            offset60_to_name,
                            last_hidden_backing,
                        ).build()
                    )
                except Exception:
                    pass

        # --- Description ---
        description: Union[str, None] = None
        self._cur.execute(
            "SELECT record_string FROM comments WHERE parent=? AND member_ref=0 LIMIT 1",
            ((r.comment_id * 0x10000) + r.cip_type,),
        )
        desc_row = self._cur.fetchone()
        if desc_row and desc_row[0]:
            description = desc_row[0]

        return DataType(name, name, string_family, class_type, children, description)


@dataclass
class ModuleBuilder(L5xElementBuilder):
    # Map from modid (u32) → module name, built by ControllerBuilder and passed in.
    _modid_to_name: Dict[int, str] = field(default_factory=dict)
    # Optional richer CIP-identity -> catalog-number table (None -> built-in only).
    _catalog_table: Union[Dict[Tuple[int, int, int], str], None] = None

    def _ip_from_data_collection(self, icp_slot: int) -> str:
        """Look up the Ethernet IP for a local backplane module via RxDataCollection.

        Local bridge modules (e.g. EN2T in the main chassis) store their IP as XML
        in hash-named children of RxDataCollection. The record for a given module
        contains its ICP slot as Type="ICP" Addr="{slot}", which uniquely identifies it.
        """
        import re as _re
        needle = f'Type="ICP" Addr="{icp_slot}"'.encode()
        # Find RxDataCollection — it is a direct child of the controller object.
        self._cur.execute(
            "SELECT object_id FROM comps WHERE comp_name='RxDataCollection' LIMIT 1"
        )
        row = self._cur.fetchone()
        if not row:
            return ""
        coll_oid = row[0]
        # Fetch all children in batches and filter in Python (SQLite LIKE on BLOBs is unreliable).
        self._cur.execute(
            "SELECT record FROM comps WHERE parent_id=?", (coll_oid,)
        )
        for (raw,) in self._cur.fetchall():
            raw = bytes(raw)
            if needle not in raw:
                continue
            m = _re.search(rb'Type="EN" Addr="([^"]+)"', raw)
            return m.group(1).decode("ascii", errors="replace") if m else ""
        return ""

    def _comms_from_data_collection(
        self, icp_slot: int, ip_address: str = ""
    ) -> "Tuple[Union[str, None], str]":
        """Extract CommMethod and ExtendedProperties public data for a module.

        Searches RxDataCollection for the hash-named child whose <in> block contains
        a Port with Type="ICP" Addr="{icp_slot}".  For Ethernet-connected modules
        (icp_slot == 0 or not found by ICP slot) a second pass matches by the
        module's IP address instead.

        Returns a 2-tuple:
          (comm_method_str_or_None, public_content_str)

        comm_method_str: the numeric string from <CF>...</CF>, or None if absent.
        public_content_str: inner content of <public>...</public>, or "" if absent.

        The record XML is often stored without the closing </public> tag (it is
        truncated in the ACD binary). We reconstruct the content by extracting
        everything after <public>.
        """
        import re as _re

        def _extract(raw: bytes) -> "Tuple[Union[str, None], str]":
            xml_start = raw.find(b'<')
            if xml_start < 0:
                return (None, "")
            xml_text = raw[xml_start:].decode("latin-1", errors="replace")
            comm_method: Union[str, None] = None
            cf_m = _re.search(r'<CF>(\d+)</CF>', xml_text)
            if cf_m:
                comm_method = cf_m.group(1)
            pub_content = ""
            pub_start = xml_text.find("<public>")
            if pub_start >= 0:
                after_pub = xml_text[pub_start + len("<public>"):]
                end_tag_m = _re.search(r'</pub', after_pub)
                if end_tag_m:
                    pub_content = after_pub[:end_tag_m.start()]
                else:
                    pub_content = after_pub.rstrip("\x00 \r\n")
            return (comm_method, pub_content)

        self._cur.execute(
            "SELECT object_id FROM comps WHERE comp_name='RxDataCollection' LIMIT 1"
        )
        row = self._cur.fetchone()
        if not row:
            return (None, "")
        coll_oid = row[0]
        self._cur.execute(
            "SELECT record FROM comps WHERE parent_id=?", (coll_oid,)
        )
        all_recs = [(bytes(raw),) for (raw,) in self._cur.fetchall()]

        # First pass: match by ICP slot.
        if icp_slot:
            needle = f'Type="ICP" Addr="{icp_slot}"'.encode()
            for (raw,) in all_recs:
                if needle in raw:
                    result = _extract(raw)
                    if result[0] is not None or result[1]:
                        return result

        # Second pass: match by IP address (for EN-connected modules).
        if ip_address:
            ip_needle = f'Addr="{ip_address}"'.encode()
            for (raw,) in all_recs:
                if ip_needle in raw:
                    result = _extract(raw)
                    if result[0] is not None or result[1]:
                        return result

        return (None, "")

    def _chassis_size_from_data_collection(self) -> "Union[int, None]":
        """Read the local backplane Bus Size from the RxDataCollection record for the CPU.

        The root controller (Local) module stores its backplane configuration as XML in a
        hash-named child of RxDataCollection.  The record contains:
          <Port Id="1" Type="ICP" Addr="0" Ups="False"><Bus Max="17" Size="7"/></Port>
        We extract the Size attribute from the Bus element on the ICP port at Addr="0".
        """
        import re as _re
        self._cur.execute(
            "SELECT object_id FROM comps WHERE comp_name='RxDataCollection' LIMIT 1"
        )
        row = self._cur.fetchone()
        if not row:
            return None
        coll_oid = row[0]
        self._cur.execute(
            "SELECT record FROM comps WHERE parent_id=?", (coll_oid,)
        )
        needle = b'Type="ICP" Addr="0"'
        for (raw,) in self._cur.fetchall():
            raw = bytes(raw)
            if needle not in raw:
                continue
            text_start = raw.find(b"<")
            if text_start < 0:
                continue
            text = raw[text_start:].decode("latin-1", errors="replace")
            m = _re.search(r'<Bus\b[^>]*\bSize="(\d+)"', text)
            if m:
                return int(m.group(1))
        return None

    def build(self) -> Module:
        self._cur.execute(
            "SELECT comp_name, object_id, record FROM comps WHERE object_id=" + str(self._object_id)
        )
        row = self._cur.fetchone()
        db_name = row[0]
        raw_rec = bytes(row[2])

        # Hex-encoded names like $02cc5e9d$ are unnamed peripheral modules (drive expansion
        # cards, etc.).  Logix Designer exports these with Name="?".
        name = "?" if (db_name.startswith("$") and db_name.endswith("$")) else db_name

        try:
            r = RxGeneric.from_bytes(raw_rec)
        except Exception:
            return Module(name, name, "", 0, 0, 0, 0, 0, "Local", 1, "false", "false")

        if r.cip_type != 0x69:
            return Module(name, name, "", 0, 0, 0, 0, 0, "Local", 1, "false", "false")

        exts: Dict[int, bytes] = {er.attribute_id: bytes(er.value) for er in r.extended_records}
        e1 = exts.get(0x001, b"")
        if len(e1) < 0x30:
            major_fault = "true" if name == "Local" else "false"
            return Module(name, name, "", 0, 0, 0, 0, 0, "Local", 1, "false", major_fault)

        vendor        = struct.unpack("<H", e1[0x02:0x04])[0]
        product_type  = struct.unpack("<H", e1[0x04:0x06])[0]
        product_code  = struct.unpack("<H", e1[0x06:0x08])[0]
        # bit 7 of the major byte is a flag; strip it to get the firmware revision.
        major         = e1[0x08] & 0x7F
        minor         = e1[0x09]
        parent_modid  = struct.unpack("<I", e1[0x16:0x1A])[0]
        parent_port   = struct.unpack("<H", e1[0x1A:0x1C])[0]
        slot          = struct.unpack("<I", e1[0x1C:0x20])[0]

        # Hash-named modules are drive peripheral expansion cards. The ACD binary stores
        # them with ProductType=123 and site-specific ProductCodes, but Logix exports them
        # all as PT=0 PC=28 (RHINOBP-DRIVE-PERIPHERAL-MODULE) without a Name attribute.
        if name == "?":
            product_type = 0
            product_code = 28

        # Resolve parent module name from the modid→name map built by ControllerBuilder.
        parent_name = self._modid_to_name.get(parent_modid, "Local")

        # MajorFault=true for the root controller module: its parent resolves to itself.
        major_fault = "true" if parent_name == name else "false"
        # bit 2 (0x04) of e1[0] → EKey Disabled (Local=0x06→Disabled, EN2T=0x11→CompatibleModule).
        ekey_state  = "Disabled" if (e1[0] & 0x04) else "CompatibleModule"

        # IP address: stored at e1[0x30] as a u16 length-prefixed ASCII string for modules
        # that connect via Ethernet upstream (parent_port == 2). Local backplane bridge
        # modules (parent_port == 1, e.g. local EN2T) leave e1[0x32] zero — their IP is
        # stored as XML in a child of RxDataCollection, keyed by ICP slot number.
        ip_address = ""
        if len(e1) > 0x32:
            ip_len = struct.unpack("<H", e1[0x30:0x32])[0]
            if ip_len:
                ip_address = e1[0x32:0x32 + ip_len].rstrip(b"\x00").decode("ascii", errors="replace")
        if not ip_address and slot:
            ip_address = self._ip_from_data_collection(slot)

        # For modules that own a remote backplane (e.g. remote chassis EN2T), the Output
        # connection record under RxMapConnectionCollection stores the chassis size at [0x4e]
        # and the module's own slot in that chassis at [0x6e].
        backplane_slot = None
        chassis_size = None
        self._cur.execute(
            "SELECT o.record FROM comps coll "
            "JOIN comps o ON o.parent_id = coll.object_id AND o.comp_name = 'Output' "
            "WHERE coll.parent_id = ? AND coll.comp_name = 'RxMapConnectionCollection'",
            (self._object_id,),
        )
        out_row = self._cur.fetchone()
        if out_row:
            out_rec = bytes(out_row[0])
            if len(out_rec) > 0x70:
                backplane_slot = struct.unpack("<H", out_rec[0x6e:0x70])[0]
                chassis_size   = struct.unpack("<H", out_rec[0x4e:0x50])[0]

        # For the root (Local) CPU module (slot=0xFFFFFFFF, self-parenting), the Output
        # connection record is absent.  The backplane chassis size is stored in the
        # RxDataCollection hash child that carries the Local module's ICP port at Addr="0".
        # Example: <Port Id="1" Type="ICP" Addr="0" Ups="False"><Bus Max="17" Size="7"/></Port>
        if chassis_size is None and slot == 0xFFFFFFFF:
            chassis_size = self._chassis_size_from_data_collection()

        # --- Description ---
        # Module descriptions are stored in the comments table keyed by
        # (comment_id * 0x10000 + cip_type), same as for tags.
        description = ""
        self._cur.execute(
            "SELECT record_string FROM comments WHERE parent=? AND member_ref=0 LIMIT 1",
            ((r.comment_id * 0x10000) + r.cip_type,),
        )
        desc_row = self._cur.fetchone()
        if desc_row:
            description = desc_row[0] or ""

        # --- Communications and ExtendedProperties ---
        # Both are extracted from the hash-named child of RxDataCollection that
        # corresponds to this module's ICP backplane slot (primary) or its IP
        # address (secondary, for EN-connected modules).
        comm_method: Union[str, None] = None
        connections: List[Tuple[str, str, str]] = []
        extended_properties = ""
        if slot or ip_address:
            comm_method, extended_properties = self._comms_from_data_collection(
                slot, ip_address
            )

        # Read individual connection records from RxMapConnectionCollection children.
        # Each child's comp_name is the connection Name in the L5X output.
        # Connection Type is inferred from the name (heuristic):
        #   names containing "output" or equal to "config" -> "Output"
        #   all others -> "Input"
        # RPI: we do not have a reliable binary decoder for the short connection
        # records seen in the test data, so we default to "0.0" (acceptable for import).
        self._cur.execute(
            "SELECT c2.comp_name FROM comps c1 "
            "JOIN comps c2 ON c2.parent_id = c1.object_id "
            "WHERE c1.parent_id = ? AND c1.comp_name = 'RxMapConnectionCollection' "
            "AND c2.comp_name NOT IN ('Output') "
            "ORDER BY c2.seq_number",
            (self._object_id,),
        )
        for (conn_name,) in self._cur.fetchall():
            name_lower = conn_name.lower()
            if "output" in name_lower or name_lower == "config":
                conn_type = "Output"
            else:
                conn_type = "Input"
            connections.append((conn_name, "0.0", conn_type))

        return Module(
            name,           # L5xElement._name (private)
            name,           # Module.name
            catalog_number_for_identity(
                (vendor, product_type, product_code), table=self._catalog_table
            ),
            vendor,
            product_type,
            product_code,
            major,
            minor,
            parent_name,
            parent_port,
            "false",        # Inhibited: always false in practice; no known bit
            major_fault,
            _ekey_state=ekey_state,
            _slot=slot,
            _ip_address=ip_address,
            _backplane_slot=backplane_slot,
            _chassis_size=chassis_size,
            _description=description,
            _comm_method=comm_method,
            _connections=connections,
            _extended_properties=extended_properties,
        )


@dataclass
class TagBuilder(L5xElementBuilder):
    @staticmethod
    def _format_rpi(microseconds: int) -> str:
        if microseconds % 1000 == 0:
            return str(microseconds // 1000)
        return f"{microseconds / 1000:.3f}"

    def _legacy_connection_descriptor(
        self, attribute_id: int, descriptor_kind: int
    ) -> bytes:
        self._cur.execute(
            "SELECT record FROM comps WHERE length(record) >= 10 "
            "AND hex(substr(record, 9, 2)) = '7E00'"
        )
        matches = []
        for (raw_record,) in self._cur.fetchall():
            try:
                parsed = RxGeneric.from_bytes(raw_record)
            except Exception:
                continue
            if parsed.cip_type != 0x7E:
                continue
            attributes = {
                item.attribute_id: bytes(item.value)
                for item in parsed.extended_records
            }
            reference = attributes.get(attribute_id, b"")
            data = attributes.get(0x01, b"")
            if (
                len(reference) >= 4
                and struct.unpack_from("<I", reference)[0] == self._object_id
                and len(data) >= 2
                and struct.unpack_from("<H", data)[0] == descriptor_kind
            ):
                matches.append(data)
        if len(matches) != 1:
            raise ValueError("Tag does not have exactly one connection descriptor")
        return matches[0]

    def _legacy_linked_data(self, extended_records: Dict[int, bytes]):
        link = extended_records.get(0x6B, b"")
        if len(link) < 4:
            raise ValueError("Tag connection does not reference linked data")
        linked_id = struct.unpack_from("<I", link)[0]
        self._cur.execute(
            "SELECT record FROM comps WHERE object_id=?",
            (linked_id,),
        )
        row = self._cur.fetchone()
        if not row:
            raise ValueError("Tag connection linked data does not exist")
        linked = RxGeneric.from_bytes(row[0])
        attributes = {
            item.attribute_id: bytes(item.value)
            for item in linked.extended_records
        }
        metadata = attributes.get(0x64, b"")
        if len(metadata) < 4:
            raise ValueError("Tag connection linked data is incomplete")
        return linked, struct.unpack_from("<I", metadata)[0]

    def _legacy_processor_minimum_rpi(self) -> int:
        self._cur.execute("SELECT record FROM comps WHERE comp_name='Local'")
        for (raw_record,) in self._cur.fetchall():
            try:
                parsed = RxGeneric.from_bytes(raw_record)
            except Exception:
                continue
            if parsed.cip_type != 0x69:
                continue
            attributes = {
                item.attribute_id: bytes(item.value)
                for item in parsed.extended_records
            }
            metadata = attributes.get(0x01, b"")
            if len(metadata) >= 8:
                device = struct.unpack_from("<HHH", metadata, 2)
                if device == (1, 14, 72):
                    return 1000
        return 0

    def _legacy_produce_info(
        self,
        extended_records: Dict[int, bytes],
    ) -> ProduceInfo:
        data = self._legacy_connection_descriptor(0x191, 0x0A)
        linked, element_size = self._legacy_linked_data(extended_records)
        if len(data) < 0x156 or struct.unpack_from("<H", data)[0] != 0x0A:
            raise ValueError(
                f"Invalid produced tag descriptor for object {self._object_id}"
            )
        if struct.unpack_from("<I", data, 0x1A)[0] != element_size:
            raise ValueError("Produced tag descriptor has the wrong element size")
        if struct.unpack_from("<I", data, 0x1E)[0] != linked.unique_tag_identifier:
            raise ValueError("Produced tag descriptor has the wrong linked data")

        minimum_rpi = max(
            struct.unpack_from("<I", data, len(data) - 0x10)[0],
            self._legacy_processor_minimum_rpi(),
        )
        maximum_rpi = struct.unpack_from("<I", data, len(data) - 0x0C)[0]
        default_rpi = struct.unpack_from("<I", data, len(data) - 0x08)[0]
        return ProduceInfo(
            "ProduceInfo",
            str(struct.unpack_from("<H", data, 0x141)[0]),
            "true" if struct.unpack_from("<I", data, 0x134)[0] else "false",
            "true" if data[0x144] else "false",
            self._format_rpi(minimum_rpi),
            self._format_rpi(maximum_rpi),
            self._format_rpi(default_rpi),
        )

    def _legacy_consume_info(
        self,
        extended_records: Dict[int, bytes],
    ) -> ConsumeInfo:
        data = self._legacy_connection_descriptor(0x190, 0x09)
        linked, element_size = self._legacy_linked_data(extended_records)
        if len(data) <= 0x143 or struct.unpack_from("<H", data)[0] != 0x09:
            raise ValueError(
                f"Invalid consumed tag descriptor for object {self._object_id}"
            )
        if struct.unpack_from("<I", data, 0x0C)[0] != element_size:
            raise ValueError("Consumed tag descriptor has the wrong element size")
        if struct.unpack_from("<I", data, 0x10)[0] != linked.unique_tag_identifier:
            raise ValueError("Consumed tag descriptor has the wrong linked data")

        remote_name_length = struct.unpack_from("<H", data, 0x22)[0]
        remote_name_end = 0x24 + remote_name_length
        if remote_name_end > len(data):
            raise ValueError("Consumed tag descriptor has an invalid remote tag")
        remote_tag = data[0x24:remote_name_end].decode("utf-8")
        unicast_value = data[0x143]
        if unicast_value not in (1, 2):
            raise ValueError("Consumed tag descriptor has an invalid unicast value")

        producer_reference = extended_records.get(0x66, b"")
        if len(producer_reference) < 4:
            raise ValueError("Consumed tag does not reference a producer")
        producer_id = struct.unpack_from("<I", producer_reference)[0]
        self._cur.execute(
            "SELECT comp_name FROM comps WHERE object_id=?",
            (producer_id,),
        )
        producer_row = self._cur.fetchone()
        if not producer_row:
            raise ValueError("Consumed tag producer does not exist")

        return ConsumeInfo(
            "ConsumeInfo",
            producer_row[0],
            remote_tag,
            str(struct.unpack_from("<H", data, 0x06)[0]),
            self._format_rpi(struct.unpack_from("<I", data, 0x02)[0]),
            "true" if unicast_value == 2 else "false",
        )

    def _legacy_data_type(self, record: LegacyRxGeneric) -> str:
        self._cur.execute(
            "SELECT comp_name, record FROM comps WHERE object_id=?",
            (record.data_instance_id,),
        )
        data_row = self._cur.fetchone()
        if data_row:
            raw_data_record = bytes(data_row[1])
            legacy_cip_type = (
                struct.unpack_from("<H", raw_data_record, 8)[0]
                if len(raw_data_record) >= 10
                else 0
            )
            if legacy_cip_type == 0x8D:
                return "MESSAGE"
            if legacy_cip_type == 0xB0:
                return "MOTION_GROUP"
            if legacy_cip_type == 0xB1:
                if record.main_record.runtime_type & 0xFF == 0xC7:
                    return "AXIS_SERVO_DRIVE"
                return "AXIS_SERVO"
            try:
                data_record = RxGeneric.from_bytes(raw_data_record)
                if data_record.cip_type == 0x6A:
                    self._cur.execute(
                        "SELECT comp_name FROM comps WHERE object_id=?",
                        (data_record.data_instance_id,),
                    )
                    type_row = self._cur.fetchone()
                    if type_row:
                        return type_row[0]
            except Exception:
                pass

        atomic_types = {
            0xC1: "BOOL",
            0xC2: "SINT",
            0xC3: "INT",
            0xC4: "DINT",
            0xC5: "LINT",
            0xC6: "USINT",
            0xC7: "UINT",
            0xC8: "UDINT",
            0xC9: "ULINT",
            0xCA: "REAL",
            0xCB: "LREAL",
        }
        return atomic_types.get(record.main_record.runtime_type & 0xFF, "")

    def _legacy_alias_for(self, value: bytes) -> str:
        if len(value) % 2 or not value.endswith(b"\x00\x00"):
            raise ValueError("Invalid legacy alias path")
        path = value.decode("utf-16-le").rstrip("\x00")

        def replace_object_id(match):
            object_id = int(match.group(1), 16)
            self._cur.execute(
                "SELECT comp_name, record FROM comps WHERE object_id=?",
                (object_id,),
            )
            row = self._cur.fetchone()
            if not row:
                raise ValueError("Legacy alias target does not exist")
            try:
                target = RxGeneric.from_bytes(row[1])
                logical_name = getattr(target, "logical_name", "")
                if logical_name:
                    return logical_name
            except Exception:
                pass
            return row[0]

        resolved = re.sub(r"@([0-9a-fA-F]{8})@", replace_object_id, path)
        if re.search(r"@[0-9a-fA-F]{8}@", resolved):
            raise ValueError("Legacy alias target could not be resolved")
        return resolved

    def build(self) -> Tag:
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id="
            + str(self._object_id)
        )
        results = self._cur.fetchall()

        # Extract ExternalAccess and Constant from the raw record at fixed offsets:
        #   raw[0x278]: ExternalAccess enum (0=Read/Write, 2=Read Only, 3=None)
        #   raw[0x279]: Constant flag (0=false, 1=true)
        raw_rec = bytes(results[0][3])
        if len(raw_rec) > 0x279:
            external_access = external_access_enum(raw_rec[0x278])
            constant = "true" if raw_rec[0x279] else None
        else:
            external_access = "Read/Write"
            constant = None

        try:
            r = RxGeneric.from_bytes(raw_rec)
        except Exception:
            return Tag(
                results[0][0], results[0][0], "Base", "", None, external_access, constant, None, 0, []
            )

        if r.cip_type != 0x6B and r.cip_type != 0x68:
            return Tag(
                results[0][0], results[0][0], "Base", "", None, external_access, constant, None, 0, []
            )

        self._cur.execute(
            "SELECT tag_reference, record_string FROM comments WHERE parent="
            + str((r.comment_id * 0x10000) + r.cip_type)
        )
        comment_results = self._cur.fetchall()

        extended_records: Dict[int, bytes] = {}
        for extended_record in r.extended_records:
            extended_records[extended_record.attribute_id] = bytes(
                extended_record.value
            )

        if isinstance(r, LegacyRxGeneric):
            metadata_name = r.logical_name
            name = metadata_name or results[0][0]
            radix = (
                radix_enum(r.main_record.radix)
                if r.main_record.radix
                else None
            )
            external_access = external_access_enum(r.main_record.external_access)

            if 0x65 in extended_records:
                return Tag(
                    name,
                    name,
                    "Alias",
                    None,
                    radix,
                    external_access,
                    None,
                    None,
                    r.main_record.data_table_instance,
                    comment_results,
                    alias_for=self._legacy_alias_for(extended_records[0x65]),
                )

            data_type = self._legacy_data_type(r)
            dimensions = [
                r.main_record.dimension_1,
                r.main_record.dimension_2,
                r.main_record.dimension_3,
            ]
            if (
                data_type == "BOOL"
                and r.main_record.runtime_type == 0x20D3
                and dimensions[0] == 1
            ):
                dimensions[0] = 32
            dimension_text = ",".join(
                str(dimension) for dimension in dimensions if dimension
            ) or None
            tag_type = "Base"
            if 0x6B in extended_records and ":" not in name:
                tag_type = "Consumed" if 0x66 in extended_records else "Produced"
            produce_info = (
                self._legacy_produce_info(extended_records)
                if tag_type == "Produced"
                else None
            )
            consume_info = (
                self._legacy_consume_info(extended_records)
                if tag_type == "Consumed"
                else None
            )
            return Tag(
                name,
                name,
                tag_type,
                data_type,
                radix,
                external_access,
                "false" if tag_type == "Produced" else None,
                dimension_text,
                r.main_record.data_table_instance,
                comment_results,
                produce_info=produce_info,
                consume_info=consume_info,
            )

        if r.main_record.data_type == 0xFFFFFFFF:
            data_type = ""
        else:
            self._cur.execute(
                "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id="
                + str(r.main_record.data_type)
            )
            data_type_results = self._cur.fetchall()
            data_type = data_type_results[0][0] if data_type_results else ""

        if 0x01 not in extended_records:
            # Name comes from comp_name in the database; radix from main_record
            raw_radix = r.main_record.radix
            radix = radix_enum(raw_radix)
            dim_parts = []
            if r.main_record.dimension_1 != 0:
                dim_parts.append(str(r.main_record.dimension_1))
            if r.main_record.dimension_2 != 0:
                dim_parts.append(str(r.main_record.dimension_2))
            if r.main_record.dimension_3 != 0:
                dim_parts.append(str(r.main_record.dimension_3))
            dimensions = ",".join(dim_parts) if dim_parts else None
            return Tag(
                results[0][0], results[0][0], "Base", data_type, radix,
                external_access, constant, dimensions, r.main_record.data_table_instance,
                comment_results,
            )

        name_length = struct.unpack("<H", extended_records[0x01][0:2])[0]
        name = bytes(extended_records[0x01][2 : name_length + 2]).decode("utf-8", errors="replace")

        raw_radix = r.main_record.radix
        radix = radix_enum(raw_radix)

        dim_parts = []
        if r.main_record.dimension_1 != 0:
            dim_parts.append(str(r.main_record.dimension_1))
        if r.main_record.dimension_2 != 0:
            dim_parts.append(str(r.main_record.dimension_2))
        if r.main_record.dimension_3 != 0:
            dim_parts.append(str(r.main_record.dimension_3))
        dimensions = ",".join(dim_parts) if dim_parts else None
        return Tag(
            name,
            name,
            "Base",
            data_type,
            radix,
            external_access,
            constant,
            dimensions,
            r.main_record.data_table_instance,
            comment_results,
        )


def _aoi_tag_usage_flags(ext01: bytes) -> int:
    """Return the usage-flags byte from an AOI tag record's ext[0x01] blob.

    Returns 0 if the record is too short.  The caller is responsible for
    interpreting the bits (0x04=Input, 0x08=Output; both set = InOut;
    neither set = local tag).
    """
    return ext01[0x20E] if len(ext01) > 0x20E else 0


def _aoi_tag_data_type(cur, raw_rec: bytes) -> str:
    """Look up the DataType name for an AOI tag record.

    The DataType OID is stored at offset 0x2A in the raw parameter record
    as a little-endian u32.  We look it up in the comps table by object_id.
    """
    if len(raw_rec) < 0x2E:
        return ""
    dt_oid = struct.unpack_from("<I", raw_rec, 0x2A)[0]
    cur.execute("SELECT comp_name FROM comps WHERE object_id=" + str(dt_oid))
    row = cur.fetchone()
    return row[0] if row else ""


@dataclass
class ParameterBuilder(L5xElementBuilder):
    """Build a Parameter from an AOI RxTagCollection child record."""

    def build(self) -> Parameter:
        self._cur.execute(
            "SELECT comp_name, record FROM comps WHERE object_id=" + str(self._object_id)
        )
        row = self._cur.fetchone()
        name = row[0]
        raw_rec = bytes(row[1])

        data_type = _aoi_tag_data_type(self._cur, raw_rec)

        # Dimensions (array size) at raw record offset 0x1A as u32; 0 means scalar.
        dimensions: Union[str, None] = None
        if len(raw_rec) >= 0x1E:
            dim_val = struct.unpack_from("<I", raw_rec, 0x1A)[0]
            if dim_val:
                dimensions = str(dim_val)

        try:
            r = RxGeneric.from_bytes(raw_rec)
            exts: Dict[int, bytes] = {
                er.attribute_id: bytes(er.value) for er in r.extended_records
            }
        except Exception:
            return Parameter(name, name, "Base", data_type, "Input", None, "false", "false", "Read/Write", None, dimensions)

        ext01 = exts.get(0x01, b"")
        flags = _aoi_tag_usage_flags(ext01)

        usage_bits = flags & 0x0C
        if usage_bits == 0x04:
            usage = "Input"
        elif usage_bits == 0x08:
            usage = "Output"
        else:
            usage = "InOut"

        required = "true" if (flags & 0x20) else "false"
        visible = "true" if (flags & 0x40) else "false"

        # ExternalAccess (u16 at ext01[0x21E])
        # MESSAGE-type InOut parameters don't carry Constant in L5X; all others do.
        if usage == "InOut":
            external_access = None
            constant: Union[str, None] = None if data_type == "MESSAGE" else "false"
        elif len(ext01) > 0x21F:
            ea_val = struct.unpack_from("<H", ext01, 0x21E)[0]
            external_access = external_access_enum(ea_val)
            constant = None
        else:
            external_access = "Read/Write"
            constant = None

        # Radix (high nibble of ext01[0x20F]).  InOut params for complex/UDT types
        # omit Radix; InOut params for scalar/array types (BOOL, INT, DINT, REAL, etc.)
        # still carry Radix in the golden L5X, so include it whenever the radix index
        # is non-zero regardless of Usage.
        if not data_type or len(ext01) <= 0x20F:
            radix: Union[str, None] = None
        else:
            radix_idx = ext01[0x20F] >> 4
            radix = radix_enum(radix_idx) if radix_idx != 0 else None

        # --- Description ---
        # Use bytes [14:18] of the comps record as member_ref to identify the
        # specific parameter description in the comments table.
        description: Union[str, None] = None
        if len(raw_rec) >= 18:
            member_ref = struct.unpack_from("<I", raw_rec, 14)[0]
            if member_ref:
                self._cur.execute(
                    "SELECT record_string FROM comments WHERE parent=? AND member_ref=? LIMIT 1",
                    ((r.comment_id * 0x10000) + r.cip_type, member_ref),
                )
                desc_row = self._cur.fetchone()
                if desc_row and desc_row[0]:
                    description = desc_row[0]

        return Parameter(
            name,
            name,
            "Base",
            data_type,
            usage,
            radix,
            required,
            visible,
            external_access,
            constant,
            dimensions,
            description,
        )


@dataclass
class LocalTagBuilder(L5xElementBuilder):
    """Build a LocalTag from an AOI RxTagCollection child record."""

    def build(self) -> LocalTag:
        self._cur.execute(
            "SELECT comp_name, record FROM comps WHERE object_id=" + str(self._object_id)
        )
        row = self._cur.fetchone()
        name = row[0]
        raw_rec = bytes(row[1])

        data_type = _aoi_tag_data_type(self._cur, raw_rec)

        # Dimensions at raw record offset 0x1A.
        dimensions: Union[str, None] = None
        if len(raw_rec) >= 0x1E:
            dim_val = struct.unpack_from("<I", raw_rec, 0x1A)[0]
            if dim_val:
                dimensions = str(dim_val)

        try:
            r = RxGeneric.from_bytes(raw_rec)
            exts: Dict[int, bytes] = {
                er.attribute_id: bytes(er.value) for er in r.extended_records
            }
        except Exception:
            return LocalTag(name, name, data_type, dimensions, None, "Read/Write")

        ext01 = exts.get(0x01, b"")
        if len(ext01) > 0x21F:
            ea_val = struct.unpack_from("<H", ext01, 0x21E)[0]
            external_access = external_access_enum(ea_val)
        else:
            external_access = "Read/Write"

        if len(ext01) > 0x20F:
            radix_idx = ext01[0x20F] >> 4
            radix: Union[str, None] = radix_enum(radix_idx) if radix_idx != 0 else None
        else:
            radix = None

        # --- Description ---
        # Use bytes [14:18] of the comps record as member_ref to identify the
        # specific local tag description in the comments table.
        description: Union[str, None] = None
        if len(raw_rec) >= 18:
            member_ref = struct.unpack_from("<I", raw_rec, 14)[0]
            if member_ref:
                self._cur.execute(
                    "SELECT record_string FROM comments WHERE parent=? AND member_ref=? LIMIT 1",
                    ((r.comment_id * 0x10000) + r.cip_type, member_ref),
                )
                desc_row = self._cur.fetchone()
                if desc_row and desc_row[0]:
                    description = desc_row[0]

        return LocalTag(name, name, data_type, dimensions, radix, external_access, description)


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
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id="
            + str(self._object_id)
        )
        results = self._cur.fetchall()

        try:
            r = RxGeneric.from_bytes(results[0][3])
        except Exception as e:
            return Routine(results[0][0], results[0][0], "", [])

        record = results[0][3]
        name = results[0][0]
        routine_type = routine_type_enum(
            struct.unpack_from("<H", r.record_buffer, 0x30)[0]
        )

        self._cur.execute(
            "SELECT rm.object_id, r.rung FROM region_map rm "
            "LEFT JOIN rungs r ON r.object_id = rm.object_id "
            "WHERE rm.parent_id=" + str(self._object_id) + " ORDER BY rm.unknown"
        )
        rows = [(row[0], row[1]) for row in self._cur.fetchall() if row[1] is not None]
        rung_ids = [row[0] for row in rows]
        rungs = [row[1] for row in rows]

        # Resolve &hexid: placeholders (object ID references) to comp names.
        # The ACD binary stores tag references as &XXXXXXXX: where XXXXXXXX is the
        # object_id in hex. Batch-resolve all unique IDs to avoid per-rung queries.
        import re as _re
        all_hex = set(_re.findall(r'&([0-9a-f]{8}):', " ".join(r for r in rungs if r)))
        if all_hex:
            id_to_name: Dict[int, str] = {}
            for hex_id in all_hex:
                oid = int(hex_id, 16)
                self._cur.execute("SELECT comp_name FROM comps WHERE object_id=?", (oid,))
                row2 = self._cur.fetchone()
                if row2:
                    id_to_name[hex_id] = row2[0]
            if id_to_name:
                def _resolve(rung: str) -> str:
                    return _re.sub(
                        r'&([0-9a-f]{8}):',
                        lambda m: (id_to_name[m.group(1)] + ":") if m.group(1) in id_to_name else m.group(0),
                        rung,
                    )
                rungs = [_resolve(r) if r else r for r in rungs]

        # Fetch rung-level comments from the comments table.
        # Rung comments are stored under the routine's own comment parent key
        # (comment_id * 0x10000 + cip_type), as AsciiRecord (record_type=1) entries
        # where rung_content != 0 (distinguishes user rung comments from internal
        # metadata strings like FBDRoutineDescription which have rung_content=0).
        # The object_id field is the 1-based rung index (rung 0 -> object_id=1).
        rung_comments: Dict[int, str] = {}
        try:
            comment_parent = (r.comment_id * 0x10000) + r.cip_type
            self._cur.execute(
                "SELECT object_id, record_string FROM comments "
                "WHERE parent=? AND record_type=1 AND rung_content!=0",
                (comment_parent,),
            )
            for obj_id, rec_str in self._cur.fetchall():
                rung_index = obj_id - 1  # convert 1-based to 0-based
                if rung_index >= 0 and rec_str and rung_index not in rung_comments:
                    rung_comments[rung_index] = rec_str
        except Exception:
            pass

        return Routine(name, name, routine_type, rungs, rung_ids, rung_comments)


def _parse_fffeff(data: bytes, offset: int):
    """Parse one fffeff-encoded string at offset. Returns (str, new_offset)."""
    if offset + 3 > len(data) or not (data[offset] == 0xFF and data[offset+1] == 0xFE and data[offset+2] == 0xFF):
        return "", offset
    length = data[offset+3]
    s = data[offset+4:offset+4+length*2].decode("utf-16-le", errors="replace")
    return s, offset + 4 + length * 2


def _filetime_to_iso(ft: int) -> str:
    """Convert a Windows FILETIME (100-ns units since 1601-01-01) to ISO8601.

    Returns "" for an empty or out-of-range value. Some AOI nameless records
    carry a corrupt FILETIME (the variable-length field walk can drift and read
    8 garbage bytes), which would otherwise overflow ``datetime`` for years
    beyond 9999 and abort the whole export with ``OverflowError``.
    """
    if not ft:
        return ""
    try:
        dt = datetime(1601, 1, 1) + timedelta(microseconds=ft // 10)
    except (OverflowError, OSError):
        return ""
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def _parse_aoi_nameless(data: bytes) -> dict:
    """Extract AOI metadata from its large nameless record."""
    result: dict = {}

    offset = 0x1A
    # Three empty fffeff strings
    for _ in range(3):
        _, offset = _parse_fffeff(data, offset)

    # 8 bytes (unknown - some kind of date, skip)
    offset += 8

    # 2-byte constant (0x0002 observed)
    offset += 2

    # CreatedBy
    result["created_by"], offset = _parse_fffeff(data, offset)

    # Software revision at creation time (skip - we want the current one later)
    _, offset = _parse_fffeff(data, offset)

    # 4 zero bytes
    offset += 4

    # Empty fffeff placeholder
    _, offset = _parse_fffeff(data, offset)

    # CreatedDate FILETIME (8 bytes, Windows FILETIME in 100-ns units)
    result["created_date"] = _filetime_to_iso(struct.unpack_from("<Q", data, offset)[0])
    offset += 8

    # EditedBy
    result["edited_by"], offset = _parse_fffeff(data, offset)

    # SoftwareRevision (current)
    result["software_revision"], offset = _parse_fffeff(data, offset)

    # 4 bytes (01 00 00 00)
    offset += 4

    # RevisionExtension
    rev_ext, offset = _parse_fffeff(data, offset)
    result["revision_extension"] = rev_ext or None

    # EditedDate FILETIME (always last 8 bytes)
    result["edited_date"] = _filetime_to_iso(struct.unpack_from("<Q", data, len(data) - 8)[0])

    return result


@dataclass
class AoiBuilder(L5xElementBuilder):
    def build(self) -> AOI:
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE object_id="
            + str(self._object_id)
        )
        results = self._cur.fetchall()

        aoi_record = bytes(results[0][3])
        name = results[0][0]

        # --- Revision (major.minor) from ext[0x01] ---
        _r_aoi: Union[RxGeneric, None] = None
        try:
            r = RxGeneric.from_bytes(aoi_record)
            _r_aoi = r
            exts: Dict[int, bytes] = {e.attribute_id: bytes(e.value) for e in r.extended_records}
            e01 = exts.get(0x01, b"")
            rev_major = struct.unpack_from("<H", e01, 0x1A)[0] if len(e01) > 0x1B else 1
            rev_minor = struct.unpack_from("<H", e01, 0x1C)[0] if len(e01) > 0x1D else 0
        except Exception:
            rev_major, rev_minor = 1, 0
        revision = f"{rev_major}.{rev_minor}"

        # --- Vendor from comps record ---
        vlen = struct.unpack_from("<H", aoi_record, 0xA6)[0] if len(aoi_record) > 0xA8 else 0
        vendor: Union[str, None] = aoi_record[0xA8:0xA8+vlen].decode("utf-8", errors="replace") if vlen > 0 else None

        # --- Metadata from large nameless record ---
        self._cur.execute(
            "SELECT record FROM nameless WHERE parent_id=" + str(self._object_id)
            + " ORDER BY LENGTH(record) DESC LIMIT 1"
        )
        nameless_row = self._cur.fetchone()
        if nameless_row and len(bytes(nameless_row[0])) > 50:
            meta = _parse_aoi_nameless(bytes(nameless_row[0]))
        else:
            meta = {"created_by": "", "created_date": "", "edited_by": "", "edited_date": "",
                    "software_revision": "", "revision_extension": None}

        parameters: List[Parameter] = []
        local_tags: List[LocalTag] = []
        routines: List[Routine] = []

        # --- Extract Parameters and LocalTags from RxTagCollection ---
        self._cur.execute(
            "SELECT object_id FROM comps WHERE parent_id="
            + str(self._object_id)
            + " AND comp_name='RxTagCollection'"
        )
        tag_coll_row = self._cur.fetchone()
        if tag_coll_row:
            tag_coll_oid = tag_coll_row[0]
            self._cur.execute(
                "SELECT object_id, record FROM comps WHERE parent_id="
                + str(tag_coll_oid)
                + " AND record_type != 512"
                + " ORDER BY seq_number"
            )
            for child_oid, child_rec in self._cur.fetchall():
                child_rec = bytes(child_rec)
                # Determine whether this is a parameter or a local tag by inspecting
                # ext01[0x20E]: bits 0x04 (Input) or 0x08 (Output) indicate a parameter.
                is_param = False
                try:
                    r_child = RxGeneric.from_bytes(child_rec)
                    exts_child: Dict[int, bytes] = {
                        er.attribute_id: bytes(er.value)
                        for er in r_child.extended_records
                    }
                    ext01 = exts_child.get(0x01, b"")
                    flags = _aoi_tag_usage_flags(ext01)
                    is_param = bool(flags & 0x0C)
                except Exception:
                    pass

                if is_param:
                    try:
                        parameters.append(ParameterBuilder(self._cur, child_oid).build())
                    except Exception:
                        pass
                else:
                    try:
                        local_tags.append(LocalTagBuilder(self._cur, child_oid).build())
                    except Exception:
                        pass

        # --- Extract Routines from RxRoutineCollection ---
        self._cur.execute(
            "SELECT object_id FROM comps WHERE parent_id="
            + str(self._object_id)
            + " AND comp_name='RxRoutineCollection'"
        )
        routine_coll_row = self._cur.fetchone()
        if routine_coll_row:
            routine_coll_oid = routine_coll_row[0]
            self._cur.execute(
                "SELECT object_id FROM comps WHERE parent_id=" + str(routine_coll_oid)
            )
            for (child_oid,) in self._cur.fetchall():
                try:
                    routines.append(RoutineBuilder(self._cur, child_oid).build())
                except Exception:
                    pass

        # --- Description + RevisionNote ---
        aoi_description: Union[str, None] = None
        revision_note = ""
        if _r_aoi is not None:
            aoi_comment_parent = (_r_aoi.comment_id * 0x10000) + _r_aoi.cip_type
            self._cur.execute(
                "SELECT record_string FROM comments WHERE parent=? AND member_ref=0 LIMIT 1",
                (aoi_comment_parent,),
            )
            desc_row = self._cur.fetchone()
            if desc_row and desc_row[0]:
                aoi_description = desc_row[0]
            try:
                self._cur.execute(
                    "SELECT record_string FROM comments WHERE parent=? AND tag_reference='__REVISION_NOTE__' LIMIT 1",
                    (aoi_comment_parent,),
                )
                rn_row = self._cur.fetchone()
                if rn_row:
                    revision_note = rn_row[0] or ""
            except Exception:
                pass

        return AOI(
            name, name, revision,
            meta["revision_extension"],
            vendor,
            "false", "false", "false",
            meta["created_date"], meta["created_by"],
            meta["edited_date"], meta["edited_by"],
            meta["software_revision"],
            parameters, local_tags, routines,
            aoi_description,
            revision_note,
        )


@dataclass
class ProgramBuilder(L5xElementBuilder):
    _data_types_map: Dict[str, "DataType"] = field(default_factory=dict)
    _redundancy_enabled: bool = field(default=False)

    def build(self) -> Program:
        self._cur.execute(
            "SELECT comp_name, record_type, record FROM comps WHERE object_id=?",
            (self._object_id,),
        )
        row = self._cur.fetchone()
        if row is None:
            raise ValueError(f"program object_id={self._object_id} was not found")

        name, record_type, record = row
        prog_record = bytes(record)
        r = RxGeneric.from_bytes(prog_record)

        # --- MainRoutineName and FaultRoutineName from extended records ---
        # ext[0x12D] = MainRoutine object_id, ext[0x066] = FaultRoutine object_id
        exts: Dict[int, bytes] = {e.attribute_id: bytes(e.value) for e in r.extended_records}
        main_routine_name: Union[str, None] = None
        fault_routine_name: Union[str, None] = None
        if 0x12D in exts and len(exts[0x12D]) >= 4:
            main_oid = struct.unpack_from("<I", exts[0x12D], 0)[0]
            if main_oid:
                self._cur.execute("SELECT comp_name FROM comps WHERE object_id=" + str(main_oid))
                row = self._cur.fetchone()
                main_routine_name = row[0] if row else None
        if 0x066 in exts and len(exts[0x066]) >= 4:
            fault_oid = struct.unpack_from("<I", exts[0x066], 0)[0]
            if fault_oid:
                self._cur.execute("SELECT comp_name FROM comps WHERE object_id=" + str(fault_oid))
                row = self._cur.fetchone()
                fault_routine_name = row[0] if row else None

        # --- Disabled flag from ext[0x01] at offset 0x24 ---
        # A u32 of 0xFFFFFFFF means the program is disabled; 0x00000000 means enabled.
        ext01 = exts.get(0x01, b"")
        disabled_flag = (
            struct.unpack_from("<I", ext01, 0x24)[0] != 0
            if len(ext01) >= 0x28
            else False
        )
        disabled = "true" if disabled_flag else "false"

        collection_id = _required_program_collection(
            self._cur,
            name,
            self._object_id,
            record_type,
            "RxRoutineCollection",
        )

        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record FROM comps WHERE parent_id="
            + str(collection_id)
        )
        routine_results = self._cur.fetchall()

        routines = []
        for child in routine_results:
            routines.append(RoutineBuilder(self._cur, child[1]).build())

        # Get the Program Scoped Tags
        tag_collection_id = _required_program_collection(
            self._cur,
            name,
            self._object_id,
            record_type,
            "RxTagCollection",
        )

        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id="
            + str(tag_collection_id)
        )
        results = self._cur.fetchall()
        tags: List[Tag] = []
        for result in results:
            tag = TagBuilder(self._cur, result[1]).build()
            tag._data_types_map = self._data_types_map
            tags.append(tag)

        self._cur.execute(
            "SELECT tag_reference, record_string FROM comments WHERE parent="
            + str((r.comment_id * 0x10000) + r.cip_type)
        )
        comment_results = self._cur.fetchall()

        # SynchronizeRedundancyDataAfterExecution: present only for redundant controllers.
        # The binary does not expose a per-program flag for this attribute — it is implicit
        # for all programs in a redundant controller project.
        sync_redundancy = "true" if self._redundancy_enabled else None

        return Program(name, name, "false", main_routine_name, fault_routine_name,
                       disabled, sync_redundancy, "false", tags, routines)


_TASK_TYPE_MAP = {1: "EVENT", 2: "PERIODIC", 4: "CONTINUOUS"}


def _program_schedule_id(record: bytes) -> int:
    parsed = RxGeneric.from_bytes(record)
    if isinstance(parsed, LegacyRxGeneric):
        metadata = next(
            (
                bytes(item.value)
                for item in parsed.extended_records
                if item.attribute_id == 0x01
            ),
            b"",
        )
        if len(metadata) < 271:
            raise ValueError("Program record does not contain a schedule ID")
        return struct.unpack_from("<I", metadata, 267)[0]
    return parsed.comment_id


@dataclass
class TaskBuilder(L5xElementBuilder):
    def build(self, comment_id_to_program: Dict[int, str]) -> Task:
        self._cur.execute(
            "SELECT comp_name, record FROM comps WHERE object_id=" + str(self._object_id)
        )
        row = self._cur.fetchone()
        name, record = row[0], row[1]

        # All task config fields live within ext[0x01], accessed via absolute BLOB offsets.
        # These offsets were reverse-engineered from CIPDemo_RevEng.ACD.
        if len(record) > 0x112E:
            task_data = record
            rate_offset = 0x106C
            type_offset = 0x10F6
            priority_offset = 0x10F8
            watchdog_offset = 0x110A
            disable_update = record[0x112E]
            program_offset = 0x5A
        else:
            parsed = RxGeneric.from_bytes(record)
            attributes = {
                item.attribute_id: bytes(item.value)
                for item in parsed.extended_records
            }
            task_data = attributes.get(0x01, b"")
            if len(task_data) < 806:
                raise ValueError("Task record does not contain configuration data")
            rate_offset = 514
            type_offset = 652
            priority_offset = 654
            watchdog_offset = 802
            disable_update = 0
            program_offset = 0

        rate_us = struct.unpack_from("<I", task_data, rate_offset)[0]
        type_val = struct.unpack_from("<H", task_data, type_offset)[0]
        priority = struct.unpack_from("<H", task_data, priority_offset)[0]
        watchdog_us = struct.unpack_from("<I", task_data, watchdog_offset)[0]

        task_type = _TASK_TYPE_MAP.get(type_val, "PERIODIC")
        rate_str = str(rate_us // 1000) if task_type != "CONTINUOUS" else None

        # Scheduled programs: ext[0x01] value starts at BLOB offset 0x5A.
        # Format: u16 count followed by N u32 comment_ids.
        prog_count = struct.unpack_from("<H", task_data, program_offset)[0]
        max_program_count = (rate_offset - program_offset - 2) // 4
        if prog_count > max_program_count:
            raise ValueError("Task record contains too many scheduled programs")
        scheduled_programs = []
        for i in range(prog_count):
            cid = struct.unpack_from(
                "<I", task_data, program_offset + 2 + i * 4
            )[0]
            prog_name = comment_id_to_program.get(cid)
            if prog_name:
                scheduled_programs.append(ScheduledProgram(prog_name, prog_name))

        event_info = None
        if task_type == "EVENT":
            event_info = EventInfo("EventInfo", "EVENT Instruction Only", "false")

        return Task(
            name,
            name,
            task_type,
            rate_str,
            str(priority),
            str(watchdog_us // 1000),
            "true" if disable_update else "false",
            "false",
            event_info,
            scheduled_programs,
        )


@dataclass
class ControllerBuilder(L5xElementBuilder):
    # Optional richer CIP-identity -> catalog-number table for resolving module
    # CatalogNumbers and the controller ProcessorType. None -> built-in only.
    _catalog_table: Union[Dict[Tuple[int, int, int], str], None] = None

    def build(self) -> Controller:
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type, record FROM comps WHERE parent_id=0 AND record_type=256"
        )
        results = self._cur.fetchall()
        if len(results) != 1:
            raise Exception("Does not contain exactly one root controller node")

        r = RxGeneric.from_bytes(results[0][4])
        self._cur.execute(
            "SELECT tag_reference, record_string FROM comments WHERE parent="
            + str((r.comment_id * 0x10000) + r.cip_type)
        )
        comment_results = self._cur.fetchall()

        extended_records: Dict[int, bytes] = {}
        for extended_record in r.extended_records:
            extended_records[extended_record.attribute_id] = bytes(
                extended_record.value
            )

        def _decode_utf16(key):
            raw = extended_records.get(key)
            if raw is None or len(raw) < 2:
                return ""
            return bytes(raw[:-2]).decode("utf-16", errors="replace")

        sfc_execution_control = _decode_utf16(0x6F)
        sfc_restart_position = _decode_utf16(0x70)
        sfc_last_scan = _decode_utf16(0x71)

        # CommPath prefix (key 0x06A): may be in kaitai extended_records (usually empty),
        # or in the LastAttributeRecord appended after the counted records (value length
        # is stored as len_value where actual data = len_value - 4 bytes, UTF-16-LE).
        _comm_path_prefix: Union[str, None] = None
        if 0x06A in extended_records:
            _cp_raw = extended_records[0x06A]
            _cp_str = _cp_raw.decode("utf-16-le", errors="replace").rstrip("\x00")
            if _cp_str:
                _comm_path_prefix = _cp_str
        else:
            # LastAttributeRecord tail: located after the (count_record - 1) parsed records.
            # Header layout: parent_id(4) + unique_tag_id(4) + record_format_version(2) +
            #   cip_type(2) + comment_id(2) = 14 bytes, then main_record(60), then
            #   len_record(4) + count_record(4) = 82 bytes total before first AttributeRecord.
            _raw_record = bytes(results[0][4])
            _rec_offset = 82
            for _er in r.extended_records:
                _rec_offset += 4 + 4 + len(bytes(_er.value))
            _tail = _raw_record[_rec_offset:]
            if len(_tail) >= 8:
                _last_attr_id = struct.unpack_from("<I", _tail, 0)[0]
                _last_len_value = struct.unpack_from("<I", _tail, 4)[0]
                if _last_attr_id == 0x06A and _last_len_value >= 4:
                    _actual_len = _last_len_value - 4
                    if len(_tail) >= 8 + _actual_len and _actual_len > 0:
                        _cp_val = _tail[8: 8 + _actual_len]
                        _cp_str = _cp_val.decode("utf-16-le", errors="replace").rstrip("\x00")
                        if _cp_str:
                            _comm_path_prefix = _cp_str

        if 0x75 in extended_records:
            sn_raw = hex(struct.unpack("<I", extended_records[0x75])[0])[2:].zfill(8)
            project_sn = f"16#{sn_raw[:4]}_{sn_raw[4:]}"
        else:
            project_sn = "Unknown"

        raw_modified_date = struct.unpack("<Q", extended_records[0x66])[0] / 10000000
        last_modified_date = (
            datetime(1601, 1, 1) + timedelta(seconds=raw_modified_date)
        ).strftime("%a %b %d %H:%M:%S %Y")

        raw_created_date = struct.unpack("<Q", extended_records[0x65])[0] / 10000000
        project_creation_date = (
            datetime(1601, 1, 1) + timedelta(seconds=raw_created_date)
        ).strftime("%a %b %d %H:%M:%S %Y")

        # MajorRev and MinorRev: derived later from the root controller module (see below)

        # MajorFaultProgram from ext[0x068] OID → comp_name lookup
        major_fault_program: Union[str, None] = None
        if 0x068 in extended_records and len(extended_records[0x068]) >= 4:
            mfp_oid = struct.unpack_from("<I", extended_records[0x068])[0]
            if mfp_oid and mfp_oid != 0xFFFFFFFF:
                self._cur.execute("SELECT comp_name FROM comps WHERE object_id=" + str(mfp_oid))
                mfp_row = self._cur.fetchone()
                major_fault_program = mfp_row[0] if mfp_row else None

        # RedundancyEnabled: controller extended record 0x001, byte offset 0x0E.
        # This byte is 0x01 for redundant controllers (e.g. 1756-L85E in redundancy mode)
        # and 0x00 for non-redundant controllers.
        _ctrl_ext001 = extended_records.get(0x001, b"")
        redundancy_enabled: bool = bool(_ctrl_ext001[0x0E]) if len(_ctrl_ext001) > 0x0E else False

        self._object_id = results[0][1]
        controller_name = results[0][0]

        # Get the data types
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id="
            + str(self._object_id)
            + " AND comp_name='RxDataTypeCollection'"
        )
        results = self._cur.fetchall()
        if len(results) > 1:
            raise Exception("Contains more than one controller data type collection")

        _data_type_id = results[0][1]
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id="
            + str(_data_type_id)
        )
        results = self._cur.fetchall()

        data_types: List[DataType] = []
        # all_data_types_map includes ProductDefined types (excluded from L5X output but
        # needed for generating Decorated XML for tags that reference those types).
        all_data_types_map: Dict[str, DataType] = {}
        for result in results:
            _data_type_object_id = result[1]
            dt = DataTypeBuilder(self._cur, _data_type_object_id).build()
            all_data_types_map[dt.name.upper()] = dt
            if dt.cls == "User":
                data_types.append(dt)

        # data_types_map: case-insensitive name → DataType for all types (User + ProductDefined).
        # Used by Tag.to_xml() when generating Decorated XML.
        data_types_map: Dict[str, DataType] = all_data_types_map

        # Get the Controller Scoped Tags
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id="
            + str(self._object_id)
            + " AND comp_name='RxTagCollection'"
        )
        results = self._cur.fetchall()
        if len(results) > 1:
            raise Exception("Contains more than one controller tag collection")
        _tag_collection_object_id = results[0][1]
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id="
            + str(_tag_collection_object_id)
        )
        results = self._cur.fetchall()
        tags: List[Tag] = []
        for result in results:
            _tag_object_id = result[1]
            tag = TagBuilder(self._cur, _tag_object_id).build()
            tag._data_types_map = data_types_map
            if (
                (tag.data_type or tag.tag_type == "Alias")
                and not tag.name.startswith("$")
                and ":" not in tag.name
                and not tag.name.startswith("__")
            ):
                tags.append(tag)

        # Get the Program Collection and get the programs
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id="
            + str(self._object_id)
            + " AND comp_name='RxProgramCollection'"
        )
        results = self._cur.fetchall()
        if len(results) > 1:
            raise Exception("Contains more than one controller program collection")

        _program_collection_object_id = results[0][1]
        program_records = _get_program_records(self._cur, _program_collection_object_id)
        programs: List[Program] = []
        for result in program_records:
            _program_object_id = result[1]
            programs.append(
                ProgramBuilder(self._cur, _program_object_id, data_types_map, redundancy_enabled).build()
            )

        # Build task schedule ID → program name map. Legacy projects keep this
        # ID in program attribute 0x01; newer records use the Rx comment ID.
        self._cur.execute(
            "SELECT comp_name, record FROM comps WHERE parent_id=" + str(_program_collection_object_id)
        )
        comment_id_to_program: Dict[int, str] = {
            _program_schedule_id(bytes(rec)): pname
            for pname, rec in self._cur.fetchall()
        }

        # Get the Task Collection and build Tasks
        self._cur.execute(
            "SELECT comp_name, object_id FROM comps WHERE parent_id="
            + str(self._object_id)
            + " AND comp_name='RxTaskCollection'"
        )
        task_coll_results = self._cur.fetchall()
        tasks: List[Task] = []
        if task_coll_results:
            _task_collection_object_id = task_coll_results[0][1]
            self._cur.execute(
                "SELECT comp_name, object_id FROM comps WHERE parent_id="
                + str(_task_collection_object_id)
                + " AND record_type=256"
            )
            for task_result in self._cur.fetchall():
                tasks.append(TaskBuilder(self._cur, task_result[1]).build(comment_id_to_program))

        # Get the AOI Collection and get the AOIs
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id="
            + str(self._object_id)
            + " AND comp_name='RxUDIDefinitionCollection'"
        )
        results = self._cur.fetchall()
        if len(results) > 1:
            raise Exception("Contains more than one AOI collection")
        _aoi_collection_object_id = results[0][1]
        self._cur.execute(
            "SELECT comp_name, object_id, parent_id, record_type FROM comps WHERE parent_id="
            + str(_aoi_collection_object_id)
            + " AND record_type=256"
        )
        results = self._cur.fetchall()
        aois: List[AOI] = []
        for result in results:
            _aoi_object_id = result[1]
            aois.append(AoiBuilder(self._cur, _aoi_object_id).build())

        # Get the Module (IO) Collection and build all Module elements.
        self._cur.execute(
            "SELECT object_id FROM comps WHERE parent_id="
            + str(self._object_id)
            + " AND comp_name='RxMapDeviceCollection'"
        )
        row = self._cur.fetchone()
        if row is None:
            modules: List[Module] = []
        else:
            coll_oid = row[0]
            self._cur.execute(
                "SELECT comp_name, object_id, record FROM comps WHERE parent_id="
                + str(coll_oid)
                + " ORDER BY seq_number"
            )
            mod_rows = self._cur.fetchall()

            # First pass: build modid→name map so child modules can resolve their parent name.
            from acd.record.rx import RxGeneric as _RxG
            modid_to_name: Dict[int, str] = {}
            for db_name, mod_oid, mod_rec in mod_rows:
                display_name = "?" if (db_name.startswith("$") and db_name.endswith("$")) else db_name
                try:
                    r = _RxG.from_bytes(bytes(mod_rec))
                    if r.cip_type == 0x69:
                        exts = {er.attribute_id: bytes(er.value) for er in r.extended_records}
                        e1 = exts.get(0x001, b"")
                        if len(e1) >= 0x30:
                            modid = struct.unpack("<I", e1[0x2C:0x30])[0]
                            modid_to_name[modid] = display_name
                except Exception:
                    pass

            # Second pass: build Module objects.
            modules = []
            for _, mod_oid, _ in mod_rows:
                modules.append(
                    ModuleBuilder(
                        self._cur, mod_oid, modid_to_name,
                        _catalog_table=self._catalog_table,
                    ).build()
                )

            # Third pass: compute (parent_name, parent_port_id) → child count,
            # then inject the relevant sub-dict into each Module as _port_child_counts.
            child_counts: Dict[tuple, int] = {}
            for m in modules:
                k = (m.parent_module, m.parent_mod_port_id)
                child_counts[k] = child_counts.get(k, 0) + 1
            for m in modules:
                m._port_child_counts = {
                    port_id: child_counts.get((m.name, port_id), 0)
                    for port_id in range(1, 20)
                    if (m.name, port_id) in child_counts
                }

        # ProcessorType is the CatalogNumber of the root controller module (the one
        # whose parent is itself, i.e. MajorFault="true").
        #
        # A3 finding (Studio 5000 v35 import): Studio reads ProcessorType to identify
        # the CPU. A real part number (e.g. "1756-L85E") imports cleanly. For an
        # out-of-table CPU the value is the CIP-triple placeholder ("CIP-1-14-216"),
        # which Studio does NOT recognise as a catalog, so it shows a "Change
        # Controller Type" dialog (observed: defaulted to 1756-L1/5550) -- the user
        # then picks the real CPU (e.g. 1756-L82E) and the import completes.
        #
        # We DELIBERATELY keep emitting the placeholder here (NOT omitting it):
        # omitting ProcessorType makes Studio unable to create the project file at
        # all ("Failed to create project file ... Couldn't be found", Error
        # 716-80042001) -- a worse outcome than the prompt. The clean fix for an
        # out-of-table CPU is to cover its identity in the external catalog (so
        # catalog_number_for_identity resolves to a real number like "1756-L82");
        # until then the placeholder degrades to a manual "Change Controller Type"
        # step, which works.
        # NOTE: the ProcessorType is derived from the CPU module's catalog_number
        # (resolved above via ModuleBuilder with self._catalog_table), so a richer
        # catalog (e.g. an external catalog merged over the built-in) flows through
        # here automatically: an out-of-table CPU that IS in the external catalog
        # gets a real ProcessorType (clean Studio import); one that is NOT still
        # gets the CIP-... placeholder (the manual "Change Controller Type" case).
        processor_type = next(
            (m.catalog_number for m in modules if m.major_fault == "true" and m.catalog_number),
            None,
        )

        # MajorRev and MinorRev come from the firmware version of the Local (backplane
        # controller) module, stored in its ext[0x01] bytes [0x08] and [0x09].
        local_module = next(
            (m for m in modules if m.name == "Local"),
            next((m for m in modules if m.major_fault == "true"), None),
        )
        if local_module is not None:
            major_rev = str(local_module.major)
            minor_rev = str(local_module.minor)
        else:
            major_rev = "0"
            minor_rev = "0"

        # CommPath: combine the stored path prefix (ends with "\") with the controller
        # module's backplane slot number (e.g. "EthernetModule\192.168.1.10\Backplane\4").
        comm_path: Union[str, None] = None
        if _comm_path_prefix is not None:
            _ctrl_slot = next(
                (m._slot for m in modules if m.major_fault == "true"), None
            )
            if _ctrl_slot is not None:
                comm_path = _comm_path_prefix + str(_ctrl_slot)

        return Controller(
            controller_name,
            "Target",
            controller_name,
            processor_type,
            major_rev,
            minor_rev,
            major_fault_program,
            project_creation_date,
            last_modified_date,
            sfc_execution_control,
            sfc_restart_position,
            sfc_last_scan,
            comm_path,
            project_sn,
            "false",        # MatchProjectToController
            "false",        # CanUseRPIFromProducer
            "0",            # InhibitAutomaticFirmwareUpdate
            "EnabledWithAppend",  # PassThroughConfiguration
            "true",         # DownloadProjectDocumentationAndExtendedProperties
            "true",         # DownloadProjectCustomProperties
            "false",        # ReportMinorOverflow
            "false",        # AutoDiagsEnabled
            "false",        # WebServerEnabled
            data_types,
            modules,
            tags,
            programs,
            tasks,
            aois,
            redundancy_enabled,
        )


@dataclass
class ProjectBuilder:
    quick_info_filename: PathLike

    def build(self) -> RSLogix5000Content:
        element = ET.parse(self.quick_info_filename)
        rslogix_content_element = element.find(".")
        if rslogix_content_element is not None:
            target_name = rslogix_content_element.attrib["Name"]

        schema_version_element = element.find("SchemaVersion")
        if schema_version_element is not None:
            schema_version_major = schema_version_element.attrib["Major"]
            schema_version_minor = schema_version_element.attrib["Minor"]
            schema_revision = f"{schema_version_major}.{schema_version_minor}"
        else:
            schema_revision = "1.0"

        # SWVersion reflects the Studio 5000 application version (e.g. "RSLogix 5000 v35.04"),
        # which is what RSLogix5000Content SoftwareRevision represents.  DeviceIdentity
        # MajorRevision/MinorRevision is the controller firmware version — a different value.
        sw_version_element = element.find("SWVersion")
        if sw_version_element is not None:
            sw_version_string = sw_version_element.attrib.get("String", "")
            # Extract the version number from the trailing "vXX.YY" portion.
            match = re.search(r"v(\d+\.\d+)$", sw_version_string.strip())
            if match:
                software_revision = match.group(1)
            else:
                # Unexpected format — fall back to DeviceIdentity firmware version.
                device_identity = element.find("DeviceIdentity")
                if device_identity is not None:
                    software_revision = (
                        f"{device_identity.attrib['MajorRevision']}"
                        f".{device_identity.attrib['MinorRevision']}"
                    )
                else:
                    software_revision = "33.01"
        else:
            # No SWVersion element — fall back to DeviceIdentity firmware version.
            device_identity = element.find("DeviceIdentity")
            if device_identity is not None:
                software_revision = (
                    f"{device_identity.attrib['MajorRevision']}"
                    f".{device_identity.attrib['MinorRevision']}"
                )
            else:
                software_revision = "33.01"

        target_type = "Controller"
        contains_context = "false"
        now = datetime.now()
        export_date = now.strftime("%a %b %d %H:%M:%S %Y")
        export_options = (
            "NoRawData L5KData DecoratedData ForceProtectedEncoding AllProjDocTrans"
        )
        return RSLogix5000Content(
            target_name,
            None,
            schema_revision,
            software_revision,
            target_name,
            target_type,
            contains_context,
            export_date,
            export_options,
        )


@dataclass
class DumpCompsRecords(L5xElementBuilder):
    base_directory: PathLike = Path("dump")

    def dump(self, parent_id: int = 0, log_file=None):
        self._cur.execute(
            f"SELECT comp_name, object_id, parent_id, record_type, record FROM comps WHERE parent_id={parent_id}"
        )
        results = self._cur.fetchall()

        for result in results:
            object_id = result[1]
            name = result[0]
            record = result[4]
            # comp_name may contain path-unsafe characters (e.g. ":" in channel
            # names on Windows). Use a sanitized component for the on-disk path;
            # keep the original name in the log so nothing is lost.
            safe_name = _sanitize_path_component(name)
            new_path = Path(os.path.join(self.base_directory, safe_name))
            if os.path.exists(os.path.join(new_path)):
                shutil.rmtree(os.path.join(new_path))
            if not os.path.exists(os.path.join(new_path)):
                os.makedirs(new_path)
            with open(Path(os.path.join(new_path, safe_name + ".dat")), "wb") as file:
                log_file.write(
                    f"Class - {struct.unpack_from('<H', result[4], 0xA)[0]} Instance {struct.unpack_from('<H', result[4], 0xC)[0]}- {name}\n"
                )
                file.write(record)

            DumpCompsRecords(self._cur, object_id, new_path).dump(object_id, log_file)
