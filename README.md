
![ACD Tools](https://github.com/hutcheb/acd/actions/workflows/acd-tools.yml/badge.svg)

## Rockwell ACD Project File Tools

The Rockwell ACD file is an archive file that contains all the files 
that are used by RSLogix/Studio 5000.

It consists of a number of text files containing version information, compressed XML
files containing project and tag information as well as a number of database files.

### Unzip

To extract the file use the acd.unzip.Unzip class

```python
from acd.unzip import Unzip

unzip = Unzip('CuteLogix.ACD')
unzip.write_files('output_directory')
```
