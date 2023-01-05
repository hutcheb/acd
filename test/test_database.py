from typing import List

import pytest

from acd.dbextract import DbExtract
from acd.sbregion import SbRegionRecord
from acd.unzip import Unzip


@pytest.fixture()
async def sample_acd():
    unzip = Unzip("../resources/CuteLogix.ACD").write_files("build")
    yield unzip


@pytest.fixture()
async def sbregion_dat():
    db = DbExtract("build/SbRegion.Dat")
    yield db


def test_open_file(sample_acd, sbregion_dat):
    assert sbregion_dat


def test_header(sample_acd, sbregion_dat):
    assert sbregion_dat.header.pointer_records_region == 2591


def test_parse_sbregion_dat(sbregion_dat):
    records: List[SbRegionRecord] = []
    for record in sbregion_dat.records:
        records.append(SbRegionRecord(record))
    assert records[-1].text == "LOWER(@f060d7ef@[6],@f060d7ef@[7]);"


def test_parse_comments_dat():
    db: DbExtract = DbExtract("build/Comments.Dat")


def test_parse_comps_dat():
    db: DbExtract = DbExtract("build/Comps.Dat")


def test_parse_nameless_dat():
    db: DbExtract = DbExtract("build/Nameless.Dat")

