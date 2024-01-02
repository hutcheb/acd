from dataclasses import dataclass
from os import PathLike

# Returned Project Structures
class Project:
    """Controller Project"""
    pass


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
        return Project()


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
        pass


@dataclass
class CompressAcdDatabase(Extract):
    """Compress database files to a Logix ACD file"""
    filename: PathLike
    output_directory: PathLike

    def compress(self):
        # Implement the compressing of an ACD file
        raise NotImplementedError
