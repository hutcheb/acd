
![ACD Tools](https://github.com/hutcheb/acd/actions/workflows/acd-tools.yml/badge.svg)

## Rockwell ACD Project File Tools

The Rockwell ACD file is an archive file that contains all the files 
that are used by RSLogix/Studio 5000.

It consists of a number of text files containing version information, compressed XML
files containing project and tag information as well as a number of database files.

### Parsing the ACD file

The exporting of the L5X file isn't complete, we are able to parse the data types, tags and programs into a Controller
python object though.

To get the Controller object and get the program/routines/rungs/tags/datatypes, use something like this
```python
from acd.export_l5x import ExportL5x

controller = ExportL5x("../resources/CuteLogix.ACD", "build/output.l5x").controller
rung = controller.programs[0].routines[0].rungs[0]
data_type = controller.data_types[-1]
tag_name = controller.tags[75].text
tag_data_type =  controller.tags[75].data_type
```

### Unzip

To extract the file use the acd.unzip.Unzip class. This extracts the database files to a directory.

```python
from acd.unzip import Unzip

unzip = Unzip('CuteLogix.ACD')
unzip.write_files('output_directory')
```



