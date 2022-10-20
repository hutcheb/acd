import pytest

from acd.unzip import Unzip


@pytest.fixture()
async def sample_acd():
    unzip = Unzip("../resources/CuteLogix.ACD")
    yield unzip


def test_open_file(sample_acd):
    assert sample_acd

def test_file_count(sample_acd):
    assert 25 == sample_acd.header.no_files


def test_header_offset(sample_acd):
    assert 2027516 == sample_acd.header.record_offset


def test_preamble_length(sample_acd):
    assert 34 == sample_acd.header.preamble_len

