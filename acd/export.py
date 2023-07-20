import re
from dataclasses import dataclass
from typing import List

from acd.comps import CompsRecord
from acd.sbregion import SbRegionRecord


@dataclass
class ExportL5X:
    sb_region_records: List[SbRegionRecord]
    comps_records: List[CompsRecord]

    def __post_init__(self):
        self.replace_tag_references()

    def replace_tag_references(self):
        for sb_rec in self.sb_region_records:
            m = re.findall("@[A-Za-z0-9]*@", sb_rec.text)
            for tag in m:
                tag_no = tag[1:-1]
                tag_id = int(tag_no, 16)
                for comp_rec in self.comps_records:
                    if tag_id == comp_rec.object_id:
                        sb_rec.text = sb_rec.text.replace(tag, comp_rec.text)
