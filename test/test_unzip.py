import pytest

from acd.unzip import Unzip


@pytest.fixture()
async def sample_acd():
    unzip = Unzip("../resources/CuteLogix.ACD")
    yield unzip


def test_open_file(sample_acd):
    assert sample_acd


def test_file_count(sample_acd):
    assert sample_acd.header.no_files == 25


def test_header_offset(sample_acd):
    assert sample_acd.header.record_offset == 2027550


def test_record_count(sample_acd):
    assert len(sample_acd.records) == 25


def test_filename(sample_acd):
    assert sample_acd.records[0].filename == "Version.Log"


def test_write_files(sample_acd):
    sample_acd.write_files("build")
