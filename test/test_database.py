import pytest

from acd.dbextract import DbExtract
from acd.unzip import Unzip


@pytest.fixture()
async def sample_acd():
    unzip = Unzip("../resources/CuteLogix.ACD").write_files("build")
    yield unzip


@pytest.fixture()
async def sample_dat():
    extract = DbExtract("build/Comps.Dat")
    yield extract


def test_open_file(sample_acd, sample_dat):
    assert sample_dat


def test_header(sample_acd, sample_dat):
    assert sample_dat.header.pointer_records_region == 2591


def test_read_record(sample_acd, sample_dat):
    assert len(sample_dat.records) == 7295
