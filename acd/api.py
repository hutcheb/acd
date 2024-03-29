from dataclasses import dataclass
from os import PathLike

from acd.l5x.elements import Controller

from acd.export_l5x import ExportL5x
from acd.unzip import Unzip


# Returned Project Structures
@dataclass
class Project:
    """Controller Project"""
    controller: Controller


# Import Export Interfaces
class ImportProject:
    """"Interface to import an PLC project"""

    def import_project(self) -> Project:
        # Import Project Interface
        pass


class ExportProject:
    """"Interface to export an PLC project"""

    def export_project(self, project: Project):
        # Export Project Interface
        pass


# Concreate examples of importing and exporting projects
@dataclass
class ImportProjectFromFile(ImportProject):
    """Import a Controller from an ACD stored on file"""
    filename: PathLike

    def import_project(self) -> Project:
        # Import Project Interface
        export = ExportL5x(self.filename, "")
        return Project(export.controller)


@dataclass
class ExportProjectToFile(ExportProject):
    """Export a Controller to an ACD file"""
    filename: PathLike

    def export_project(self, project: Project):
        # Concreate example of exporting a Project Object to an ACD file
        raise NotImplementedError


# Extracting/Compressing files from an ACD file Interfaces
class Extract:
    """Base class for all extract functions"""

    def extract(self):
        # Interface for extracting database files
        pass


class Compress:
    """Base class for all compress functions"""

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
