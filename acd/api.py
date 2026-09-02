import os
import tempfile
import shutil
import xml.dom.minidom
from abc import abstractmethod
from dataclasses import dataclass
from os import PathLike
from pathlib import Path

from acd.integrity import (
    FILEINFO_LENGTH,
    compute_fileinfo,
    detect_fileinfo_selector,
    expected_key_length_for_selector,
    find_fileinfo_offset,
    get_fileinfo_key,
)
from acd.l5x.export_l5x import ExportL5x
from acd.zip.unzip import Unzip
from acd.zip.write_acd import build_acd_bytes, write_acd
from acd.zip.write_dat import patch_sbregion_dat

from acd.database.acd_database import AcdDatabase
from acd.l5x.elements import DumpCompsRecords, RSLogix5000Content


# Clean top-level API

def load_acd(path, temp_dir: str = None) -> RSLogix5000Content:
    """Load an ACD file into a Python object model.

    Args:
        path: Path to the .ACD file.
        temp_dir: Directory for SQLite and extracted files.  A temporary
            directory is created and cleaned up automatically if omitted.

    Returns:
        RSLogix5000Content with a fully populated controller object tree.
        The project also carries _raw_files / _file_order / _footer_unknown
        for use by save_acd().
    """
    cleanup = temp_dir is None
    if cleanup:
        temp_dir = tempfile.mkdtemp(prefix="acd_load_")
    try:
        exporter = ExportL5x(str(path), temp_dir)
        return exporter.project
    finally:
        if cleanup:
            shutil.rmtree(temp_dir, ignore_errors=True)


def save_acd(project: RSLogix5000Content, output_path) -> None:
    """Write a project object model back to an ACD file.

    The project must have been loaded via load_acd() or ExportL5x so that
    it carries _raw_files, _file_order, and _footer_unknown.

    If the project has had `acd.integrity.set_fileinfo_key(project, key)`
    called on it, the container's `FileInfo.Dat` is recomputed here so
    that the Logix Designer SDK accepts the file. The algorithm is
    auto-selected by key length (32 bytes = modern Studio, 126 bytes =
    older Studio); the key length must match the source ACD's
    FileInfo.Dat selector or a ValueError is raised.

    Without a registered key, the container is written as-is (suitable
    for byte-equal round-trips, but the SDK will reject any output
    where covered streams were modified).

    Args:
        project: Project loaded by load_acd().
        output_path: Destination .ACD file path.

    Raises:
        ValueError: if a key is registered whose length doesn't match
            the source ACD's FileInfo.Dat selector.
    """
    container = build_acd_bytes(
        files=project._raw_files,
        file_order=project._file_order,
        footer_unknown=project._footer_unknown,
    )

    key = get_fileinfo_key(project)
    if key is not None:
        fi_offset = find_fileinfo_offset(container)
        source_selector = detect_fileinfo_selector(container, fi_offset)
        expected_key_len = expected_key_length_for_selector(source_selector)
        if len(key) != expected_key_len:
            raise ValueError(
                f"ACD's FileInfo.Dat uses selector {source_selector:#06x} "
                f"requiring a {expected_key_len}-byte key; the registered "
                f"key is {len(key)} bytes. Register the correct key for "
                f"this ACD's Studio version."
            )
        new_fi = compute_fileinfo(container, fi_offset, key=key)
        container = (
            container[:fi_offset]
            + new_fi
            + container[fi_offset + FILEINFO_LENGTH:]
        )

    Path(output_path).write_bytes(container)


def patch_rungs(project: RSLogix5000Content, changes: dict) -> None:
    """Patch rung text in a loaded project's SbRegion.Dat in-place.

    Call this before save_acd() to modify ladder rung logic.

    Args:
        project: Project loaded by load_acd().
        changes: Mapping of {rung_object_id: new_rung_text}.

            rung_object_id — the integer object_id for the rung.  Available
            as routine._rung_ids[i] for the i-th rung in a Routine.

            new_rung_text — the new rung text with plain tag names (not
            @HEX@ placeholders).  Tag names are resolved back to object_id
            placeholders automatically using project._id_to_name.

    Example:
        project = load_acd("project.ACD")
        routine = project.controller.programs[0].routines[0]
        changes = {routine._rung_ids[0]: "XIC(MyTag)OTE(OutputTag);"}
        patch_rungs(project, changes)
        save_acd(project, "modified.ACD")
    """
    project._raw_files["SbRegion.Dat"] = patch_sbregion_dat(
        project._raw_files["SbRegion.Dat"],
        changes,
        project._id_to_name,
    )


# Returned Project Structures


# Import Export Interfaces
class ImportProject:
    """ "Interface to import an PLC project"""

    @abstractmethod
    def import_project(self) -> RSLogix5000Content:
        # Import Project Interface
        pass


class ExportProject:
    """ "Interface to export an PLC project"""

    @abstractmethod
    def export_project(self, project: RSLogix5000Content):
        # Export Project Interface
        pass


# Concreate examples of importing and exporting projects
@dataclass
class ImportProjectFromFile(ImportProject):
    """Import a Controller from an ACD stored on file"""

    filename: PathLike

    def import_project(self) -> RSLogix5000Content:
        # Import Project Interface
        export = ExportL5x(self.filename)
        return export.project


@dataclass
class ExportProjectToFile(ExportProject):
    """Export a Controller to an ACD file"""

    filename: PathLike

    def export_project(self, project: RSLogix5000Content):
        # Concreate example of exporting a Project Object to an ACD file
        raise NotImplementedError


# Extracting/Compressing files from an ACD file Interfaces
class Extract:
    """Base class for all extract functions"""

    @abstractmethod
    def extract(self):
        # Interface for extracting database files
        pass


class Compress:
    """Base class for all compress functions"""

    @abstractmethod
    def compress(self):
        # Interface for extracting database files
        pass


# Concreate examples of extracting and compressing ACD files
@dataclass
class ExtractAcdDatabase(Extract):
    """Extract database files from a Logix ACD file"""

    filename: PathLike
    output_directory: PathLike

    def extract(self):
        # Implement the extraction of an ACD file
        unzip = Unzip(self.filename)
        unzip.write_files(self.output_directory)


@dataclass
class CompressAcdDatabase(Extract):
    """Compress database files to a Logix ACD file"""

    filename: PathLike
    output_directory: PathLike

    def compress(self):
        # Implement the compressing of an ACD file
        raise NotImplementedError


@dataclass
class ExtractAcdDatabaseRecordsToFiles(ExportProject):
    """Export all ACD databases to a raw database record tree"""

    filename: PathLike
    output_directory: PathLike

    def extract(self):
        # Implement the extraction of an ACD file
        database = AcdDatabase(self.filename, self.output_directory)
        database.extract_to_file()


@dataclass
class DumpCompsRecordsToFile(ExportProject):
    """
    Dump the Comps database to a folder. Each individual record can then be navigated and viewed.

    :param str filename: Filename of ACD file
    :param str output_directory: Location to store the records
    """

    filename: PathLike
    output_directory: PathLike

    def extract(self):
        export = ExportL5x(self.filename)
        # The README documents dumping to a fresh directory
        # (DumpCompsRecordsToFile("My.ACD", "output/")). Ensure that directory
        # exists before writing output.log into it; previously a non-existent
        # output_directory raised FileNotFoundError.
        os.makedirs(self.output_directory, exist_ok=True)
        with open(
            os.path.join(self.output_directory, "output.log"),
            "w",
        ) as log_file:
            # Write the record tree into the same output_directory (previously
            # it defaulted to "./dump", so output.log and the tree ended up in
            # different places).
            DumpCompsRecords(
                export._cur, 0, base_directory=self.output_directory
            ).dump(log_file=log_file)


@dataclass
class ConvertAcdToL5x(Extract):
    """Convert an ACD file to an L5X XML file.

    Parses the ACD binary databases (Comps.Dat, SbRegion.Dat, Comments.Dat)
    and serialises the in-memory project model to an L5X-compatible XML file
    that can be imported back into Studio 5000 Logix Designer.

    The output captures controller tags, programs, routines (ladder rungs),
    data types (UDTs), add-on instructions (AOIs), and hardware modules.

    :param PathLike acd_filename: Path to the source .ACD file.
    :param PathLike l5x_filename: Path for the output .L5X file.
    :param bool pretty_print: Pretty-print the XML output (default True).
    """

    acd_filename: PathLike
    l5x_filename: PathLike
    pretty_print: bool = True

    def extract(self):
        project = ImportProjectFromFile(self.acd_filename).import_project()
        raw_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + project.to_xml()
        if self.pretty_print:
            try:
                dom = xml.dom.minidom.parseString(raw_xml.encode("utf-8"))
                output = dom.toprettyxml(indent="  ", encoding="UTF-8").decode("utf-8")
                # minidom adds its own XML declaration; strip the duplicate header
                lines = output.splitlines()
                if lines and lines[0].startswith("<?xml"):
                    lines[0] = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                output = "\n".join(lines)
            except Exception:
                output = raw_xml
        else:
            output = raw_xml
        with open(self.l5x_filename, "w", encoding="utf-8") as f:
            f.write(output)
