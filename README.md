

![PyPI](https://img.shields.io/pypi/v/acd-tools?label=acd-tools)
![PyPI - Downloads](https://img.shields.io/pypi/dm/acd-tools)
![ACD Tools](https://github.com/hutcheb/acd/actions/workflows/acd-tools.yml/badge.svg)

## Rockwell ACD Project File Tools

The Rockwell ACD file is an archive file that contains all the files 
that are used by RSLogix/Studio 5000.

It consists of a number of text files containing version information, compressed XML
files containing project and tag information as well as a number of database files.

This library allows you to unzip all the files and extract information from these files.

### Installing

To install acd tools from pypi run

```bash
pip install acd-tools
```

### Parsing the ACD file

To get the Controller object and get the program/routines/rungs/tags/datatypes, use something like this
```python
from acd.api import ImportProjectFromFile

controller = ImportProjectFromFile("../resources/CuteLogix.ACD").import_project().controller
rung = controller.programs[0].routines[0].rungs[0]
data_type = controller.data_types[-1]
tag_name = controller.tags[75].text
tag_data_type =  controller.tags[75].data_type
```

### Unzip

To extract the file use the acd.api.ExtractAcdDatabase class. This extracts the database files to a directory.

```python
from acd.api import ExtractAcdDatabase

ExtractAcdDatabase('CuteLogix.ACD', 'output_directory').extract()

```

### Extract Raw Records From ACD Files

A select number of database files contain interesting information. This will save each database record to a file
to make it easier to see whats in them.

```python
from acd.api import ExtractAcdDatabaseRecordsToFiles

ExtractAcdDatabaseRecordsToFiles('CuteLogix.ACD', 'output_directory').extract()

```

### Dump Comps Database Records

The Comps database contains a lot of information and can be export as a directory structure to make it easier to look at.

```python
from acd.api import DumpCompsRecordsToFile

DumpCompsRecordsToFile('CuteLogix.ACD', 'output_directory').extract()

```

### Converting from ACD to L5X

This hasn't been started but could be feasible eventually.
