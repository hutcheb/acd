import pytest

from acd.dbextract import DbExtract


@pytest.fixture()
async def sample_dat():
    extract = DbExtract("../resources/SbRegion.Dat")
    yield extract


def test_open_file(sample_dat):
    assert sample_dat


def test_header(sample_dat):
    assert sample_dat.header.pointer_records_region == 2591


def test_read_record(sample_dat):
    assert len(sample_dat.records) == 133
